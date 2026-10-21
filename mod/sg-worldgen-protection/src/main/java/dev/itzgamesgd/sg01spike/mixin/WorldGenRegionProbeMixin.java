package dev.itzgamesgd.sg01spike.mixin;

import dev.itzgamesgd.sg01spike.Probe;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Experiment-only probe (Phase 4): observes WorldGenRegion reads made from the guard. Never changes a result. */
@Mixin(WorldGenRegion.class)
public abstract class WorldGenRegionProbeMixin {
    @Inject(method = "hasChunk", at = @At("RETURN"), require = 1)
    private void sg01spike$hasChunk(int chunkX, int chunkZ, CallbackInfoReturnable<Boolean> cir) {
        if (Probe.inGuard()) Probe.recordHasChunk(cir.getReturnValue());
    }

    @Inject(method = "getChunk(IILnet/minecraft/world/level/chunk/status/ChunkStatus;Z)Lnet/minecraft/world/level/chunk/ChunkAccess;", at = @At("HEAD"), require = 1)
    private void sg01spike$getChunkCall(int chunkX, int chunkZ, ChunkStatus targetStatus, boolean loadOrGenerate, CallbackInfoReturnable<ChunkAccess> cir) {
        if (Probe.inGuard()) Probe.REGION_GET_CALLS.incrementAndGet();
    }

    @Inject(method = "getChunk(IILnet/minecraft/world/level/chunk/status/ChunkStatus;Z)Lnet/minecraft/world/level/chunk/ChunkAccess;", at = @At("RETURN"), require = 1)
    private void sg01spike$getChunkReturn(int chunkX, int chunkZ, ChunkStatus targetStatus, boolean loadOrGenerate, CallbackInfoReturnable<ChunkAccess> cir) {
        if (Probe.inGuard()) Probe.recordRegionGet(targetStatus, cir.getReturnValue());
    }
}
