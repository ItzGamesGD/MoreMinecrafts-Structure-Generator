package dev.itzgamesgd.sg01spike.mixin;

import dev.itzgamesgd.sg01spike.Guard;
import dev.itzgamesgd.sg01spike.GuardMarker;
import dev.itzgamesgd.sg01spike.MonsterRoomGeometry;
import dev.itzgamesgd.sg01spike.MonsterRoomOracle;
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
            MonsterRoomOracle.begin(Guard.MONSTER_ROOM, level, origin);
            return;
        }
        List<BoundingBox> reaches;
        if (Guard.REFINE == Guard.Refine.PRECHECK) {
            Probe.enter();
            try {
                reaches = MonsterRoomGeometry.passingBoxes(level, origin);
            } finally {
                Probe.exit();
            }
        } else {
            // N7-A reach: origin +-4 horizontally, y -1..+4 (the union of every variant's footprint).
            reaches = List.of(MonsterRoomGeometry.maxBox(origin));
        }
        if (Guard.shouldCancel(Guard.MONSTER_ROOM, level, origin, reaches)) {
            cir.setReturnValue(false);
        }
    }

    @Inject(method = "place", at = @At("RETURN"), require = 1)
    private void sg01spike$oracle(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin, CallbackInfoReturnable<Boolean> cir) {
        if (Guard.ORACLE_MONSTER_ROOM) MonsterRoomOracle.end(Guard.MONSTER_ROOM, level, origin);
    }
}
