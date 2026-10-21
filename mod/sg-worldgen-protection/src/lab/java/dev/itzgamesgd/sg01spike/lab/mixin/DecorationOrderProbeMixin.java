package dev.itzgamesgd.sg01spike.lab.mixin;

import dev.itzgamesgd.sg01spike.lab.Probe;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.StructureManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Experiment-only probe (N7-A4 Phase 5): records the order in which chunks run their feature-decoration step. Never changes a result. */
@Mixin(ChunkGenerator.class)
public abstract class DecorationOrderProbeMixin {
    @Inject(method = "applyBiomeDecoration", at = @At("HEAD"), require = 1)
    private void sg01spike$order(WorldGenLevel level, ChunkAccess chunk, StructureManager structureManager, CallbackInfo ci) {
        Probe.recordDecoration(chunk.getPos().x(), chunk.getPos().z());
    }
}
