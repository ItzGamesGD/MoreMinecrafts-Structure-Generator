package dev.itzgamesgd.sg01spike.mixin;

import dev.itzgamesgd.sg01spike.DriftGuard;
import dev.itzgamesgd.sg01spike.Guard;
import dev.itzgamesgd.sg01spike.GuardMarker;
import dev.itzgamesgd.sg01spike.LabHooks;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.feature.GeodeFeature;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(GeodeFeature.class)
public abstract class GeodeFeatureMixin implements GuardMarker {
    @Inject(method = "place", at = @At("HEAD"), cancellable = true, require = 1)
    private void sg01spike$guard(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin, CallbackInfoReturnable<Boolean> cir) {
        // Lab-only fixture for causal attribution (selected by the lab mod only). Never active in production.
        LabHooks lab = LabHooks.get();
        LabHooks.Config cfg = lab.config();
        if (cfg.fixture() == Guard.Fixture.NO_GEODE) {
            cir.setReturnValue(false);
            return;
        }
        DriftGuard.discard();
        lab.mark();
        GeodeFeature self = (GeodeFeature) (Object) this;
        // GeodeFeature.place iterates BlockPos.betweenClosed(origin + minGenOffset, origin + maxGenOffset) and places crystals on pos.relative(direction)
        // of positions inside it, so the hard bound of its writes is that box grown by one cell (N7-C, from the 26.3 bytecode; verified by DriftGuard).
        int shrink = cfg.fault() == Guard.Fault.GEODE_SHRUNK ? 6 : 0; // lab fault: simulates vanilla writing beyond the bound the module believes
        BoundingBox reach = new BoundingBox(
                origin.getX() + self.minGenOffset() - 1 + shrink, origin.getY() + self.minGenOffset() - 1 + shrink, origin.getZ() + self.minGenOffset() - 1 + shrink,
                origin.getX() + self.maxGenOffset() + 1 - shrink, origin.getY() + self.maxGenOffset() + 1 - shrink, origin.getZ() + self.maxGenOffset() + 1 - shrink);
        DriftGuard.Level levelBefore = DriftGuard.GEODE.level();
        boolean cancel;
        if (levelBefore == DriftGuard.Level.VERIFIED) {
            cancel = Guard.shouldCancel(Guard.GEODE, level, origin, reach);
        } else {
            // PROVISIONAL / ZONE: no assumption about the footprint; correct for any vanilla behaviour
            BoundingBox zone = DriftGuard.zone(level);
            cancel = Guard.shouldCancel(Guard.GEODE, level, origin, List.of(zone == null ? reach : zone));
        }
        lab.decisionDone(true);
        if (cancel) {
            if (levelBefore != DriftGuard.Level.VERIFIED) {
                DriftGuard.GEODE.unverifiedCancels.incrementAndGet();
                lab.unverifiedCancel(true, level, origin, reach);
            }
            lab.placeDone(true, false);
            cir.setReturnValue(false);
            return;
        }
        DriftGuard.State state = DriftGuard.GEODE;
        BoundingBox around = Guard.inflate(reach, 3);
        if (state.level() == DriftGuard.Level.VERIFIED && Guard.piecesNear(level, around)) {
            state.nearMisses.incrementAndGet();
            DriftGuard.arm(state, level, around, List.of(reach), reach);
        } else if (state.shouldSample()) {
            DriftGuard.arm(state, level, around, List.of(reach), reach);
        }
    }

    @Inject(method = "place", at = @At("RETURN"), require = 1)
    private void sg01spike$return(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin, CallbackInfoReturnable<Boolean> cir) {
        DriftGuard.end(level, origin);
        LabHooks.get().placeDone(true, true);
    }
}
