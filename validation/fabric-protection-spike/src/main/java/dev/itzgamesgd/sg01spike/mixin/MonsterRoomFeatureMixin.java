package dev.itzgamesgd.sg01spike.mixin;

import dev.itzgamesgd.sg01spike.Guard;
import dev.itzgamesgd.sg01spike.GuardMarker;
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
        // MonsterRoomFeature.place: xr, zr in 2..3, walls at +-(r+1) => +-4 horizontally; y from -1 to 4.
        BoundingBox reach = new BoundingBox(origin.getX() - 4, origin.getY() - 1, origin.getZ() - 4, origin.getX() + 4, origin.getY() + 4, origin.getZ() + 4);
        if (Guard.shouldCancel(Guard.MONSTER_ROOM, level, origin, reach)) {
            cir.setReturnValue(false);
        }
    }
}
