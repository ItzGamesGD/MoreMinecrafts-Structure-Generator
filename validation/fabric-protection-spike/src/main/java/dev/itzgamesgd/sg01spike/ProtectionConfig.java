package dev.itzgamesgd.sg01spike;

import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.Set;
import net.minecraft.core.HolderSet;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.levelgen.structure.Structure;

/** Resolves the protected structure set from a datapack structure tag. A missing or empty tag is a hard failure. */
public final class ProtectionConfig {
    public static final Identifier TAG_ID = Identifier.parse("moreminecrafts:protected_from_overlays");
    private static volatile Set<Structure> protectedStructures;

    private ProtectionConfig() {
    }

    /** Reload policy (manifest mode): a reload that would break the contract is rejected, the last validated set stays in force, and the rejection is loud. */
    public static void reload(MinecraftServer server) {
        if (!MANIFEST_MODE) {
            resolve(server);
            return;
        }
        try {
            resolve(server);
        } catch (RuntimeException e) {
            reloadRejections++;
            lastRejection = e.getMessage();
            SpikeMod.LOGGER.error("SG_SPIKE protection data rejected on reload, keeping the last validated protection set ({} structures): {}",
                    protectedStructures == null ? 0 : protectedStructures.size(), e.getMessage());
        }
    }

    public static int protectedCountOrZero() {
        Set<Structure> set = protectedStructures;
        return set == null ? 0 : set.size();
    }

    public static Set<Structure> protectedStructures() {
        Set<Structure> set = protectedStructures;
        if (set == null) {
            throw new IllegalStateException("SG protection spike: protected structure set was never resolved (ServerStarted did not run)");
        }
        return set;
    }

    /** SG01_PROTECTION = legacy (default, merged structure tag) | manifest (versioned manifest + additive extensions, N7-A4). */
    public static final boolean MANIFEST_MODE = "manifest".equalsIgnoreCase(System.getProperty("sg01.protection", System.getenv("SG01_PROTECTION")));
    public static volatile ProtectionContract.Result contract;
    public static volatile int reloadRejections;
    public static volatile String lastRejection;

    public static void resolve(MinecraftServer server) {
        if (MANIFEST_MODE) {
            ProtectionContract.Result result = ProtectionContract.validate(server);
            protectedStructures = result.effective();
            contract = result;
            SpikeMod.LOGGER.info("SG_SPIKE protection contract OK: owner={} format={} revision={} required={} extensions={} effective={}", result.owner(),
                    result.format(), result.revision(), result.required(), result.extensions(), result.effective().size());
            result.warnings().forEach(w -> SpikeMod.LOGGER.warn("SG_SPIKE protection contract warning: {}", w));
            return;
        }
        Registry<Structure> registry = server.registryAccess().lookupOrThrow(Registries.STRUCTURE);
        TagKey<Structure> tag = TagKey.create(Registries.STRUCTURE, TAG_ID);
        HolderSet.Named<Structure> holders = registry.get(tag).orElseThrow(
                () -> new IllegalStateException("SG protection spike: required structure tag #" + TAG_ID + " is missing"));
        Set<Structure> resolved = Collections.newSetFromMap(new IdentityHashMap<>());
        holders.forEach(holder -> resolved.add(holder.value()));
        if (resolved.isEmpty()) {
            throw new IllegalStateException("SG protection spike: structure tag #" + TAG_ID
                    + " resolves to no structure (is the SG datapack loaded?)");
        }
        protectedStructures = resolved;
        SpikeMod.LOGGER.info("SG_SPIKE protected structures resolved from #{}: {} structure(s)", TAG_ID, resolved.size());
    }
}
