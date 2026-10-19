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

    public static Set<Structure> protectedStructures() {
        Set<Structure> set = protectedStructures;
        if (set == null) {
            throw new IllegalStateException("SG protection spike: protected structure set was never resolved (ServerStarted did not run)");
        }
        return set;
    }

    public static void resolve(MinecraftServer server) {
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
