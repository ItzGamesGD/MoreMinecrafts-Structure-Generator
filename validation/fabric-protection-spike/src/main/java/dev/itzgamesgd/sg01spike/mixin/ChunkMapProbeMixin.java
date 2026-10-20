package dev.itzgamesgd.sg01spike.mixin;

import dev.itzgamesgd.sg01spike.Probe;
import net.minecraft.server.level.ChunkMap;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@SuppressWarnings("rawtypes")
/** Experiment-only probe (Phase 4): records any generation task scheduled while the guard runs. Never changes a result. */
@Mixin(ChunkMap.class)
public abstract class ChunkMapProbeMixin {
    @Inject(method = "scheduleGenerationTask", at = @At("HEAD"), require = 1)
    private void sg01spike$schedule(ChunkStatus targetStatus, ChunkPos pos, CallbackInfoReturnable cir) {
        if (Probe.inGuard()) {
            Probe.CHUNKMAP_SCHEDULE.incrementAndGet();
            Probe.recordScheduled("ChunkMap.scheduleGenerationTask", targetStatus, pos);
        }
    }
}
