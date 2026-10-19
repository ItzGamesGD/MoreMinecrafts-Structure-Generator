package dev.itzgamesgd.sg01spike.mixin;

import dev.itzgamesgd.sg01spike.Guard;
import dev.itzgamesgd.sg01spike.GuardMarker;
import dev.itzgamesgd.sg01spike.MonsterRoomGeometry;
import dev.itzgamesgd.sg01spike.MonsterRoomOracle;
import dev.itzgamesgd.sg01spike.Perf;
import dev.itzgamesgd.sg01spike.Probe;
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
        if (Guard.ORACLE_MONSTER_ROOM) {
            List<BoundingBox> refined;
            Probe.enter();
            try {
                refined = MonsterRoomGeometry.passingBoxes(level, origin);
            } finally {
                Probe.exit();
            }
            MonsterRoomOracle.begin(Guard.MONSTER_ROOM, level, origin, refined);
            return;
        }
        Perf.mark();
        boolean cancel;
        switch (Guard.REFINE) {
            case HYBRID -> cancel = Guard.shouldCancelHybrid(Guard.MONSTER_ROOM, level, origin, MonsterRoomGeometry.maxBox(origin),
                    () -> refinedBoxes(level, origin));
            case PRECHECK -> cancel = Guard.shouldCancel(Guard.MONSTER_ROOM, level, origin, refinedBoxes(level, origin));
            default -> cancel = Guard.shouldCancel(Guard.MONSTER_ROOM, level, origin, List.of(MonsterRoomGeometry.maxBox(origin)));
        }
        Perf.decisionDone(Perf.MONSTER_DECISION_NS, Perf.MONSTER_DECISION_BYTES);
        if (cancel) {
            cir.setReturnValue(false);
            Perf.placeDone(Perf.MONSTER_PLACE_NS, null);
        }
    }

    @Inject(method = "place", at = @At("RETURN"), require = 1)
    private void sg01spike$return(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin, CallbackInfoReturnable<Boolean> cir) {
        if (Guard.ORACLE_MONSTER_ROOM) {
            MonsterRoomOracle.end(Guard.MONSTER_ROOM, level, origin);
            return;
        }
        Perf.placeDone(Perf.MONSTER_PLACE_NS, Perf.MONSTER_VANILLA_NS);
    }

    private static List<BoundingBox> refinedBoxes(WorldGenLevel level, BlockPos origin) {
        Probe.enter();
        try {
            return MonsterRoomGeometry.passingBoxes(level, origin);
        } finally {
            Probe.exit();
        }
    }
}
