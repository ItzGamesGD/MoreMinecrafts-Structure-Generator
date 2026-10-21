package dev.itzgamesgd.sg01spike.mixin;

import dev.itzgamesgd.sg01spike.Probe;
import net.minecraft.server.level.ServerChunkCache;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@SuppressWarnings("rawtypes")
/** Experiment-only probe (Phase 4): counts blocking and future-based chunk requests made from the guard. Never changes a result. */
@Mixin(ServerChunkCache.class)
public abstract class ServerChunkCacheProbeMixin {
    @Inject(method = "getChunk(IILnet/minecraft/world/level/chunk/status/ChunkStatus;Z)Lnet/minecraft/world/level/chunk/ChunkAccess;", at = @At("HEAD"), require = 1)
    private void sg01spike$blocking(int x, int z, ChunkStatus targetStatus, boolean loadOrGenerate, CallbackInfoReturnable cir) {
        if (Probe.inGuard()) Probe.SERVER_GET_BLOCKING.incrementAndGet();
    }

    @Inject(method = "getChunkFuture", at = @At("HEAD"), require = 1)
    private void sg01spike$future(int x, int z, ChunkStatus targetStatus, boolean loadOrGenerate, CallbackInfoReturnable cir) {
        if (Probe.inGuard()) Probe.SERVER_GET_FUTURE.incrementAndGet();
    }
}
