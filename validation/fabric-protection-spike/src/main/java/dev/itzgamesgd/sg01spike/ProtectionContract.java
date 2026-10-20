package dev.itzgamesgd.sg01spike;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.packs.repository.Pack;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.world.level.levelgen.structure.Structure;

/**
 * Experimental protection-data contract (N7-A4, model C). The structure-owning datapack ships a versioned manifest; the module declares which
 * manifest formats and which minimum revision it supports. The manifest is authoritative for REQUIRED structures. A separate tag is the only
 * extension point, and it is additive-only: it is read from each pack's file, not from the merged tag, so a "replace" cannot remove anything.
 *
 * Every failure is an IllegalStateException with a stable code (ContractViolation) so that a missing, stale, conflicting or incompatible
 * protection source can never silently disable protection. Declared pack formats of unrelated datapacks are never inspected.
 */
public final class ProtectionContract {
    public static final Identifier MANIFEST = Identifier.parse("moreminecrafts:sg_protection/manifest.json");
    public static final Identifier EXTENSION_TAG_FILE = Identifier.parse("moreminecrafts:tags/worldgen/structure/protected_extensions.json");
    /** Manifest formats this module build understands. */
    public static final Set<Integer> SUPPORTED_FORMATS = Set.of(1);
    /** Lowest manifest revision this build accepts; older data predates structures the module must protect. */
    public static final int MIN_REVISION = 1;

    public static final class ContractViolation extends IllegalStateException {
        public final String code;

        ContractViolation(String code, String message) {
            super("SG protection contract [" + code + "]: " + message);
            this.code = code;
        }
    }

    public record Result(Set<Structure> effective, String owner, int format, int revision, int required, int extensions, List<String> warnings) {
    }

    private ProtectionContract() {
    }

    public static Result validate(MinecraftServer server) {
        List<String> warnings = new ArrayList<>();
        var resources = server.getResourceManager();
        List<Resource> providers = resources.getResourceStack(MANIFEST);
        if (providers.isEmpty()) {
            throw new ContractViolation("MANIFEST_MISSING", "no pack provides " + MANIFEST + " (is the SG datapack loaded?)");
        }
        if (providers.size() > 1) {
            List<String> ids = new ArrayList<>();
            providers.forEach(p -> ids.add(p.sourcePackId()));
            throw new ContractViolation("MANIFEST_CONFLICT", MANIFEST + " is provided by several packs " + ids + "; exactly one owner is allowed");
        }
        Resource manifest = providers.get(0);
        String owner = manifest.sourcePackId();
        JsonObject json;
        try (Reader reader = manifest.openAsReader()) {
            json = JsonParser.parseReader(reader).getAsJsonObject();
        } catch (IOException | RuntimeException e) {
            throw new ContractViolation("MANIFEST_INVALID", "cannot parse " + MANIFEST + " from " + owner + ": " + e.getMessage());
        }
        int format = intField(json, "format");
        if (!SUPPORTED_FORMATS.contains(format)) {
            throw new ContractViolation("FORMAT_UNSUPPORTED", "manifest from " + owner + " has format " + format + ", this module supports " + SUPPORTED_FORMATS);
        }
        int revision = intField(json, "revision");
        if (revision < MIN_REVISION) {
            throw new ContractViolation("MANIFEST_STALE", "manifest from " + owner + " has revision " + revision + ", this module requires at least " + MIN_REVISION);
        }
        // Scoped to the owning pack only: other datapacks' declared formats are never inspected.
        Pack ownerPack = server.getPackRepository().getPack(owner);
        if (ownerPack != null && !ownerPack.getCompatibility().isCompatible()) {
            throw new ContractViolation("OWNER_PACK_INCOMPATIBLE", "the pack that owns the protection manifest (" + owner + ") declares a format that is "
                    + ownerPack.getCompatibility() + " for this game version");
        }
        Registry<Structure> registry = server.registryAccess().lookupOrThrow(Registries.STRUCTURE);
        Set<Structure> effective = Collections.newSetFromMap(new IdentityHashMap<>());
        Set<String> requiredIds = new LinkedHashSet<>();
        JsonArray required = json.has("structures") && json.get("structures").isJsonArray() ? json.getAsJsonArray("structures") : new JsonArray();
        for (JsonElement e : required) requiredIds.add(e.getAsString());
        if (requiredIds.isEmpty()) {
            throw new ContractViolation("MANIFEST_EMPTY", "manifest from " + owner + " lists no required structure");
        }
        for (String id : requiredIds) {
            Optional<Holder.Reference<Structure>> holder = registry.get(ResourceKey.create(Registries.STRUCTURE, Identifier.parse(id)));
            if (holder.isEmpty()) {
                throw new ContractViolation("REQUIRED_UNRESOLVED", "required structure " + id + " (manifest from " + owner + ") is not in the structure registry");
            }
            effective.add(holder.get().value());
        }
        int added = 0;
        for (Resource ext : server.getResourceManager().getResourceStack(EXTENSION_TAG_FILE)) {
            try (Reader reader = ext.openAsReader()) {
                JsonObject tag = JsonParser.parseReader(reader).getAsJsonObject();
                if (tag.has("replace") && tag.get("replace").getAsBoolean()) {
                    warnings.add("extension file from " + ext.sourcePackId() + " sets replace=true; ignored (extensions are additive-only)");
                }
                JsonArray values = tag.has("values") ? tag.getAsJsonArray("values") : new JsonArray();
                for (JsonElement v : values) {
                    String id = v.isJsonObject() ? v.getAsJsonObject().get("id").getAsString() : v.getAsString();
                    if (id.startsWith("#")) {
                        warnings.add("extension " + id + " from " + ext.sourcePackId() + " is a tag reference; not supported, ignored");
                        continue;
                    }
                    Optional<Holder.Reference<Structure>> holder = registry.get(ResourceKey.create(Registries.STRUCTURE, Identifier.parse(id)));
                    if (holder.isEmpty()) {
                        warnings.add("extension " + id + " from " + ext.sourcePackId() + " is not in the structure registry; ignored");
                    } else if (effective.add(holder.get().value())) {
                        added++;
                    }
                }
            } catch (IOException | RuntimeException e) {
                warnings.add("extension file from " + ext.sourcePackId() + " could not be read: " + e.getMessage());
            }
        }
        return new Result(effective, owner, format, revision, requiredIds.size(), added, warnings);
    }

    private static int intField(JsonObject json, String name) {
        if (!json.has(name) || !json.get(name).isJsonPrimitive()) {
            throw new ContractViolation("MANIFEST_INVALID", "manifest has no integer field '" + name + "'");
        }
        try {
            return json.get(name).getAsInt();
        } catch (RuntimeException e) {
            throw new ContractViolation("MANIFEST_INVALID", "manifest field '" + name + "' is not an integer");
        }
    }
}
