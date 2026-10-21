package dev.itzgamesgd.sgprotection.mixin;

import dev.itzgamesgd.sgprotection.DriftGuard;
import dev.itzgamesgd.sgprotection.Guard;
import dev.itzgamesgd.sgprotection.GuardMarker;
import dev.itzgamesgd.sgprotection.MonsterRoomGeometry;
import dev.itzgamesgd.sgprotection.LabHooks;
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
    private void sgprotection$guard(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin, CallbackInfoReturnable<Boolean> cir) {
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
        if (!Guard.hookActive("monster_room")) return; // the write-level guard protects; the feature runs untouched
        DriftGuard.discard();
        lab.mark();
        BoundingBox broad = MonsterRoomGeometry.maxBox(origin);
        // lab fault: the module believes the footprint is smaller than it is (the real bound stays what vanilla does)
        if (cfg.fault() == Guard.Fault.BOX_SHRUNK) broad = new BoundingBox(broad.minX() + 2, broad.minY() + 1, broad.minZ() + 2, broad.maxX() - 2, broad.maxY() - 1, broad.maxZ() - 2);
        DriftGuard.Level levelBefore = DriftGuard.MONSTER_ROOM.level();
        boolean cancel;
        switch (DriftGuard.monsterRoomRefine(cfg.refine())) {
            case HYBRID -> cancel = Guard.shouldCancelHybrid(Guard.MONSTER_ROOM, level, origin, broad, () -> sgprotection$refinedBoxes(level, origin));
            case PRECHECK -> cancel = Guard.shouldCancel(Guard.MONSTER_ROOM, level, origin, sgprotection$refinedBoxes(level, origin));
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
            // box guard (production): only the footprint bound is checked; the replicated precheck is evaluated only when a lab configuration uses it
            boolean replica = cfg.refine() == Guard.Refine.HYBRID || cfg.refine() == Guard.Refine.PRECHECK;
            DriftGuard.arm(DriftGuard.MONSTER_ROOM, level, Guard.inflate(broad, 2), replica ? sgprotection$refinedBoxes(level, origin) : List.of(broad), broad);
        }
    }

    @Inject(method = "place", at = @At("RETURN"), require = 1)
    private void sgprotection$return(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin, CallbackInfoReturnable<Boolean> cir) {
        LabHooks lab = LabHooks.get();
        if (lab.config().oracle()) {
            lab.oracleEnd(Guard.MONSTER_ROOM, level, origin);
            return;
        }
        DriftGuard.end(level, origin);
        lab.placeDone(false, true);
    }

    private static List<BoundingBox> sgprotection$refinedBoxes(WorldGenLevel level, BlockPos origin) {
        LabHooks lab = LabHooks.get();
        lab.enter();
        try {
            return MonsterRoomGeometry.passingBoxes(level, origin);
        } finally {
            lab.exit();
        }
    }
}
