package dev.itzgamesgd.sg01spike;

import java.util.Set;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.levelgen.structure.Structure;

/**
 * Holds the validated protected-structure set. The only source is the versioned manifest contract ({@link ProtectionContract}); the legacy
 * merged-tag mode of the N7-A spike was removed. Startup validation failures abort the server start. A datapack reload that violates the
 * contract is rejected loudly and the last validated set stays in force: a reload can never weaken protection.
 */
public final class ProtectionConfig {
    private static volatile Set<Structure> protectedStructures;
    public static volatile ProtectionContract.Result contract;
    public static volatile int reloadRejections;
    public static volatile String lastRejection;

    private ProtectionConfig() {
    }

    /** Startup: any violation propagates and aborts the server start. */
    public static void resolve(MinecraftServer server) {
        ProtectionContract.Result result = ProtectionContract.validate(server);
        protectedStructures = result.effective();
        contract = result;
        SpikeMod.LOGGER.info("SG_SPIKE protection contract OK: owner={} format={} revision={} required={} extensions={} effective={}", result.owner(),
                result.format(), result.revision(), result.required(), result.extensions(), result.effective().size());
        result.warnings().forEach(w -> SpikeMod.LOGGER.warn("SG_SPIKE protection contract warning: {}", w));
        result.rejectedExtensions().forEach(r -> SpikeMod.LOGGER.error("SG_SPIKE protection extension REJECTED (the owner's protection is unaffected, the extension's structures are NOT protected): {}", r));
    }

    /** Datapack reload: a rejected reload keeps the last validated set. */
    public static void reload(MinecraftServer server) {
        try {
            resolve(server);
        } catch (RuntimeException e) {
            reloadRejections++;
            lastRejection = e.getMessage();
            SpikeMod.LOGGER.error("SG_SPIKE protection data rejected on reload, keeping the last validated protection set ({} structures): {}",
                    protectedCountOrZero(), e.getMessage());
        }
    }

    public static int protectedCountOrZero() {
        Set<Structure> set = protectedStructures;
        return set == null ? 0 : set.size();
    }

    public static Set<Structure> protectedStructures() {
        Set<Structure> set = protectedStructures;
        if (set == null) {
            throw new IllegalStateException("SG protection: protected structure set was never resolved (ServerStarting did not run)");
        }
        return set;
    }
}
