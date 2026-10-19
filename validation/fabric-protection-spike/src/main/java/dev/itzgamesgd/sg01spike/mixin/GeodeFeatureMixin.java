package dev.itzgamesgd.sg01spike.mixin;

import dev.itzgamesgd.sg01spike.Guard;
import dev.itzgamesgd.sg01spike.GuardMarker;
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
        // Experiment-only fixture for causal attribution (SG01_FIXTURE=no_geode). Never shipped.
        if (Guard.FIXTURE == Guard.Fixture.NO_GEODE) {
            cir.setReturnValue(false);
            return;
        }
        GeodeFeature self = (GeodeFeature) (Object) this;
        // Hard bound of GeodeFeature.place: it only writes inside origin + [minGenOffset, maxGenOffset] on every axis.
        BoundingBox reach = new BoundingBox(
                origin.getX() + self.minGenOffset(), origin.getY() + self.minGenOffset(), origin.getZ() + self.minGenOffset(),
                origin.getX() + self.maxGenOffset(), origin.getY() + self.maxGenOffset(), origin.getZ() + self.maxGenOffset());
        if (Guard.shouldCancel(Guard.GEODE, level, origin, reach)) {
            cir.setReturnValue(false);
        }
    }
}
