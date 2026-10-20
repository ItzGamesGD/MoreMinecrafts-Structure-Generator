package dev.itzgamesgd.sg01spike;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.IdentityHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import net.minecraft.SharedConstants;
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
 * Protection-data contract (N7-B, model C of the N7-A4 report). The structure-owning datapack ships a versioned manifest at
 * {@code data/moreminecrafts/sg_protection/manifest.json}; the module declares which manifest formats and which minimum revision it supports.
 * The manifest is authoritative for the REQUIRED structures. The only extension point is a tag file that is additive-only: it is read from each
 * pack's own file (never from the merged tag), so a {@code "replace": true} in another pack cannot remove or override anything.
 *
 * There is exactly one source of protection data. The legacy merged-tag mode of the N7-A spike no longer exists: an absent, stale, conflicting,
 * malformed or incompatible source is a {@link ContractViolation} with a stable code and a remedy, so protection can never be silently
 * disabled. Declared pack formats of unrelated datapacks are never inspected.
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

        ContractViolation(String code, String message, String remedy) {
            super("SG protection contract [" + code + "]: " + message + " Remedy: " + remedy);
            this.code = code;
        }
    }

    /** {@code warnings} entries start with a stable code, e.g. {@code EXTENSION_DUPLICATE: ...}. */
    public record Result(Set<Structure> effective, String owner, int format, int revision, int required, int extensions, List<String> warnings) {
    }

    private ProtectionContract() {
    }

    public static Result validate(MinecraftServer server) {
        List<String> warnings = new ArrayList<>();
        var resources = server.getResourceManager();
        List<Resource> providers = resources.getResourceStack(MANIFEST);
        if (providers.isEmpty()) {
            throw new ContractViolation("MANIFEST_MISSING", "no pack provides " + MANIFEST + ".",
                    "enable the structure-owning SG datapack (it ships data/moreminecrafts/sg_protection/manifest.json); the guard refuses to run without it.");
        }
        if (providers.size() > 1) {
            List<String> ids = new ArrayList<>();
            providers.forEach(p -> ids.add(p.sourcePackId()));
            throw new ContractViolation("MANIFEST_CONFLICT", MANIFEST + " is provided by several packs " + ids + "; exactly one owner is allowed.",
                    "remove or disable all but the structure-owning pack's copy of the manifest.");
        }
        Resource manifest = providers.get(0);
        String owner = manifest.sourcePackId();
        JsonObject json;
        try (Reader reader = manifest.openAsReader()) {
            json = JsonParser.parseReader(reader).getAsJsonObject();
        } catch (IOException | RuntimeException e) {
            throw new ContractViolation("MANIFEST_INVALID", "cannot parse " + MANIFEST + " from " + owner + " as a JSON object (" + e.getMessage() + ").",
                    "regenerate the SG datapack, or fix the JSON syntax of the manifest.");
        }
        int format = intField(json, "format", owner);
        if (!SUPPORTED_FORMATS.contains(format)) {
            throw new ContractViolation("FORMAT_UNSUPPORTED", "manifest from " + owner + " has format " + format + ", this module supports " + SUPPORTED_FORMATS + ".",
                    "install a version of the SG datapack and of this module that agree on the manifest format.");
        }
        int revision = intField(json, "revision", owner);
        if (revision < MIN_REVISION) {
            throw new ContractViolation("MANIFEST_STALE", "manifest from " + owner + " has revision " + revision + ", this module requires at least " + MIN_REVISION + ".",
                    "update the SG datapack; an older revision may not list every structure that must be protected.");
        }
        if (json.has("minecraft")) {
            String declared = json.get("minecraft").isJsonPrimitive() ? json.get("minecraft").getAsString() : "";
            String running = SharedConstants.getCurrentVersion().name();
            if (!declared.equals(running)) {
                throw new ContractViolation("GAME_VERSION_MISMATCH", "manifest from " + owner + " was written for Minecraft '" + declared + "', this server runs '" + running + "'.",
                        "use the SG datapack build that targets this Minecraft version.");
            }
        }
        // Scoped to the owning pack only: other datapacks' declared formats are never inspected.
        Pack ownerPack = server.getPackRepository().getPack(owner);
        if (ownerPack != null && !ownerPack.getCompatibility().isCompatible()) {
            throw new ContractViolation("OWNER_PACK_INCOMPATIBLE", "the pack that owns the protection manifest (" + owner + ") declares a format that is "
                    + ownerPack.getCompatibility() + " for this game version.", "use the SG datapack build that targets this Minecraft version.");
        }
        Registry<Structure> registry = server.registryAccess().lookupOrThrow(Registries.STRUCTURE);
        Set<Structure> effective = Collections.newSetFromMap(new IdentityHashMap<>());
        Set<Identifier> requiredIds = new LinkedHashSet<>();
        if (!json.has("structures") || !json.get("structures").isJsonArray()) {
            throw new ContractViolation("MANIFEST_INVALID", "manifest from " + owner + " has no 'structures' array.", "list the structure ids that must be protected.");
        }
        for (JsonElement e : json.getAsJsonArray("structures")) {
            Identifier id = e.isJsonPrimitive() && e.getAsJsonPrimitive().isString() ? Identifier.tryParse(e.getAsString()) : null;
            if (id == null) {
                throw new ContractViolation("MANIFEST_INVALID", "manifest from " + owner + " has a 'structures' entry that is not a valid structure id: " + e + ".",
                        "use plain namespaced id strings such as \"moreminecrafts:forgotten_kingdom/central_cavern\".");
            }
            if (!requiredIds.add(id)) {
                throw new ContractViolation("MANIFEST_INVALID", "manifest from " + owner + " lists " + id + " more than once.", "remove the duplicate entry.");
            }
        }
        if (requiredIds.isEmpty()) {
            throw new ContractViolation("MANIFEST_EMPTY", "manifest from " + owner + " lists no required structure.", "list at least the structure the pack owns.");
        }
        for (Identifier id : requiredIds) {
            Optional<Holder.Reference<Structure>> holder = registry.get(ResourceKey.create(Registries.STRUCTURE, id));
            if (holder.isEmpty()) {
                throw new ContractViolation("REQUIRED_UNRESOLVED", "required structure " + id + " (manifest from " + owner + ") is not in the structure registry.",
                        "ship the structure definition in the same pack, or remove the entry from the manifest.");
            }
            effective.add(holder.get().value());
            // Ownership: the manifest owner must itself define every structure it asks to protect.
            Identifier definition = Identifier.fromNamespaceAndPath(id.getNamespace(), "worldgen/structure/" + id.getPath() + ".json");
            List<Resource> definers = resources.getResourceStack(definition);
            List<String> definerIds = new ArrayList<>();
            definers.forEach(d -> definerIds.add(d.sourcePackId()));
            if (!definerIds.contains(owner)) {
                throw new ContractViolation("OWNERSHIP_MISMATCH", "manifest owner " + owner + " does not define required structure " + id + " (defined by " + definerIds + ").",
                        "only the pack that defines a structure may declare it required; list it in an extension file instead.");
            }
            if (!definerIds.get(definerIds.size() - 1).equals(owner)) {
                warnings.add("STRUCTURE_OVERRIDDEN: the definition of required structure " + id + " is overridden by pack " + definerIds.get(definerIds.size() - 1)
                        + "; protection applies to the active definition.");
            }
        }
        int added = 0;
        Set<Identifier> seenExtensions = new HashSet<>();
        for (Resource ext : resources.getResourceStack(EXTENSION_TAG_FILE)) {
            String from = ext.sourcePackId();
            JsonObject tag;
            try (Reader reader = ext.openAsReader()) {
                tag = JsonParser.parseReader(reader).getAsJsonObject();
            } catch (IOException | RuntimeException e) {
                throw new ContractViolation("EXTENSION_MALFORMED", "extension file " + EXTENSION_TAG_FILE + " from pack " + from + " cannot be parsed (" + e.getMessage() + ").",
                        "fix or remove that pack's protected_extensions.json.");
            }
            if (tag.has("replace") && tag.get("replace").isJsonPrimitive() && tag.get("replace").getAsBoolean()) {
                throw new ContractViolation("EXTENSION_REPLACE_FORBIDDEN", "extension file from pack " + from + " sets replace=true, but extensions are additive-only.",
                        "remove \"replace\" from that pack's protected_extensions.json; it cannot remove or override the owner's protected structures.");
            }
            if (!tag.has("values") || !tag.get("values").isJsonArray()) {
                throw new ContractViolation("EXTENSION_MALFORMED", "extension file from pack " + from + " has no 'values' array.", "add a 'values' array of structure ids.");
            }
            for (JsonElement v : tag.getAsJsonArray("values")) {
                String raw;
                boolean mandatory = true;
                if (v.isJsonPrimitive() && v.getAsJsonPrimitive().isString()) {
                    raw = v.getAsString();
                } else if (v.isJsonObject() && v.getAsJsonObject().has("id") && v.getAsJsonObject().get("id").isJsonPrimitive()) {
                    raw = v.getAsJsonObject().get("id").getAsString();
                    JsonElement req = v.getAsJsonObject().get("required");
                    if (req != null) {
                        if (!req.isJsonPrimitive() || !req.getAsJsonPrimitive().isBoolean()) {
                            throw new ContractViolation("EXTENSION_MALFORMED", "extension entry " + v + " from pack " + from + " has a non-boolean 'required'.", "use true or false.");
                        }
                        mandatory = req.getAsBoolean();
                    }
                } else {
                    throw new ContractViolation("EXTENSION_MALFORMED", "extension entry " + v + " from pack " + from + " is neither an id string nor {\"id\": ...}.",
                            "use \"namespace:structure\" strings or {\"id\": \"namespace:structure\", \"required\": false} objects.");
                }
                Identifier id = raw.startsWith("#") ? null : Identifier.tryParse(raw);
                if (id == null) {
                    throw new ContractViolation("EXTENSION_MALFORMED", "extension entry '" + raw + "' from pack " + from + " is not a valid structure id (tag references are not supported).",
                            "list structure ids only.");
                }
                Optional<Holder.Reference<Structure>> holder = registry.get(ResourceKey.create(Registries.STRUCTURE, id));
                if (holder.isEmpty()) {
                    if (mandatory) {
                        throw new ContractViolation("EXTENSION_UNRESOLVED", "required extension entry " + id + " from pack " + from + " is not in the structure registry.",
                                "install the pack that defines it, or mark the entry {\"id\": ..., \"required\": false}.");
                    }
                    warnings.add("EXTENSION_OPTIONAL_UNRESOLVED: optional extension " + id + " from pack " + from + " is not in the structure registry; ignored.");
                    continue;
                }
                if (requiredIds.contains(id)) {
                    warnings.add("EXTENSION_DUPLICATE: extension " + id + " from pack " + from + " is already required by the manifest; no effect.");
                } else if (!seenExtensions.add(id)) {
                    warnings.add("EXTENSION_DUPLICATE: extension " + id + " from pack " + from + " is already added by another entry; no effect.");
                } else if (effective.add(holder.get().value())) {
                    added++;
                }
            }
        }
        return new Result(effective, owner, format, revision, requiredIds.size(), added, warnings);
    }

    private static int intField(JsonObject json, String name, String owner) {
        if (!json.has(name) || !json.get(name).isJsonPrimitive()) {
            throw new ContractViolation("MANIFEST_INVALID", "manifest from " + owner + " has no integer field '" + name + "'.", "add \"" + name + "\": <integer>.");
        }
        try {
            return json.get(name).getAsInt();
        } catch (RuntimeException e) {
            throw new ContractViolation("MANIFEST_INVALID", "manifest field '" + name + "' from " + owner + " is not an integer.", "use an integer value.");
        }
    }
}
