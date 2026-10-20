package dev.itzgamesgd.sg01spike.mixin;

import dev.itzgamesgd.sg01spike.Probe;
import net.minecraft.server.level.ChunkMap;
import net.minecraft.server.level.GenerationChunkHolder;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@SuppressWarnings("rawtypes")
/** Experiment-only probe (Phase 4): records generation tasks scheduled through a holder while the guard runs. Never changes a result. */
@Mixin(GenerationChunkHolder.class)
public abstract class GenerationChunkHolderProbeMixin {
    @Inject(method = "scheduleChunkGenerationTask", at = @At("HEAD"), require = 1)
    private void sg01spike$schedule(ChunkStatus status, ChunkMap scheduler, CallbackInfoReturnable cir) {
        if (Probe.inGuard()) {
            Probe.HOLDER_SCHEDULE.incrementAndGet();
            Probe.recordScheduled("GenerationChunkHolder.scheduleChunkGenerationTask", status, null);
        }
    }
}
