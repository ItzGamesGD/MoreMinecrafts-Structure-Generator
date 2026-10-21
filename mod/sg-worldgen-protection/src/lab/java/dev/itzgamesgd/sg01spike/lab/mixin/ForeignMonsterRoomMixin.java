package dev.itzgamesgd.sg01spike.lab.mixin;

import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.feature.MonsterRoomFeature;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Lab-only stand-in for "another mod transforms MonsterRoomFeature": an inert handler that only adds a method to the loaded class. */
@Mixin(MonsterRoomFeature.class)
public abstract class ForeignMonsterRoomMixin {
    @Inject(method = "place", at = @At("HEAD"), require = 1)
    private void labforeign$inert(WorldGenLevel level, ChunkGenerator generator, RandomSource random, BlockPos origin, CallbackInfoReturnable<Boolean> cir) {
    }
}
