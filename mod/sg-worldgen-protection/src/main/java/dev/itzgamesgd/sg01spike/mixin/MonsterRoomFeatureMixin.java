package dev.itzgamesgd.sg01spike.mixin;

import dev.itzgamesgd.sg01spike.DriftGuard;
import dev.itzgamesgd.sg01spike.Guard;
import dev.itzgamesgd.sg01spike.GuardMarker;
import dev.itzgamesgd.sg01spike.MonsterRoomGeometry;
import dev.itzgamesgd.sg01spike.LabHooks;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.feature.MonsterRoomFeature;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(MonsterRoomFeature.class)
public abstract class MonsterRoomFeatureMixin implements GuardMarker {
    @Inject(method = "place", at = @At("HEAD"), cancellable = true, require = 1)
    private void sg01spike$guard(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin, CallbackInfoReturnable<Boolean> cir) {
        LabHooks lab = LabHooks.get();
        LabHooks.Config cfg = lab.config();
        if (cfg.fault() == Guard.Fault.ZONE_PROBE) lab.zoneProbe(level, origin);
        if (cfg.oracle()) {
            List<BoundingBox> refined;
            lab.enter();
            try {
                refined = MonsterRoomGeometry.passingBoxes(level, origin);
            } finally {
                lab.exit();
            }
            lab.oracleBegin(Guard.MONSTER_ROOM, level, origin, refined);
            return;
        }
        DriftGuard.discard();
        lab.mark();
        BoundingBox broad = MonsterRoomGeometry.maxBox(origin);
        DriftGuard.Level levelBefore = DriftGuard.MONSTER_ROOM.level();
        boolean cancel;
        switch (DriftGuard.monsterRoomRefine(cfg.refine())) {
            case HYBRID -> cancel = Guard.shouldCancelHybrid(Guard.MONSTER_ROOM, level, origin, broad, () -> sg01spike$refinedBoxes(level, origin));
            case PRECHECK -> cancel = Guard.shouldCancel(Guard.MONSTER_ROOM, level, origin, sg01spike$refinedBoxes(level, origin));
            case ZONE -> {
                BoundingBox zone = DriftGuard.zone(level);
                cancel = Guard.shouldCancel(Guard.MONSTER_ROOM, level, origin, List.of(zone == null ? broad : zone));
            }
            default -> cancel = Guard.shouldCancel(Guard.MONSTER_ROOM, level, origin, List.of(broad));
        }
        lab.decisionDone(false);
        if (cancel) {
            if (levelBefore != DriftGuard.Level.VERIFIED) {
                DriftGuard.MONSTER_ROOM.unverifiedCancels.incrementAndGet();
                lab.unverifiedCancel(false, level, origin, null);
            }
            DriftGuard.discard();
            cir.setReturnValue(false);
            lab.placeDone(false, false);
        } else if (!DriftGuard.isArmed() && DriftGuard.MONSTER_ROOM.shouldSample()) {
            // Differential verification of an attempt that is safe even if the model is wrong (no protected piece within the box, or verified).
            DriftGuard.arm(DriftGuard.MONSTER_ROOM, level, Guard.inflate(broad, 2), sg01spike$refinedBoxes(level, origin), broad);
        }
    }

    @Inject(method = "place", at = @At("RETURN"), require = 1)
    private void sg01spike$return(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin, CallbackInfoReturnable<Boolean> cir) {
        LabHooks lab = LabHooks.get();
        if (lab.config().oracle()) {
            lab.oracleEnd(Guard.MONSTER_ROOM, level, origin);
            return;
        }
        DriftGuard.end(level, origin);
        lab.placeDone(false, true);
    }

    private static List<BoundingBox> sg01spike$refinedBoxes(WorldGenLevel level, BlockPos origin) {
        LabHooks lab = LabHooks.get();
        lab.enter();
        try {
            return MonsterRoomGeometry.passingBoxes(level, origin);
        } finally {
            lab.exit();
        }
    }
}
