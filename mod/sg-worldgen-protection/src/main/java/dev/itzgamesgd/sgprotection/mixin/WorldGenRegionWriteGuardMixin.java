package dev.itzgamesgd.sgprotection.mixin;

import dev.itzgamesgd.sgprotection.WriteGuard;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Refuses block writes into the piece boxes of protected structures during world generation (see WriteGuard). Reads only; never writes a block itself. */
@Mixin(WorldGenRegion.class)
public abstract class WorldGenRegionWriteGuardMixin {
    @Unique
    private WriteGuard.Zone sgprotection$zone;

    @Inject(method = "setBlock", at = @At("HEAD"), cancellable = true, require = 1)
    private void sgprotection$guardWrite(BlockPos pos, BlockState state, int flags, int recursionLeft, CallbackInfoReturnable<Boolean> cir) {
        if (!WriteGuard.enabled()) return;
        WriteGuard.Zone zone = sgprotection$zone;
        if (zone == null) {
            zone = WriteGuard.zoneFor((WorldGenRegion) (Object) this);
            sgprotection$zone = zone;
        }
        if (!zone.isEmpty() && WriteGuard.blocked(zone, pos)) cir.setReturnValue(false);
    }
}
