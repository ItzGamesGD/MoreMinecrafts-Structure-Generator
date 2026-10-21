package dev.itzgamesgd.sgprotection;

import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.core.BlockPos;

/**
 * Vanilla-drift protection for the two hooked features (N7-C). Both guards rest on assumptions about vanilla (the write footprint of a geode, the
 * footprint and read-only precheck of a monster room). A guard that cannot establish those assumptions must not rely on them, and the fallback must
 * hold WITHOUT them. Per feature this class keeps a {@link Level}:
 *
 * PROVISIONAL (initial): the footprint bound is not yet verified in this process, so neither feature relies on it: both use ZONE. Allowed attempts
 *   (no protected piece anywhere in the zone, hence harmless even if the model is wrong) are verified differentially (below) and the level is promoted
 *   once enough attempts agreed with the model.
 * VERIFIED: the box decision (monster room: the N7-A reach, union of all variant footprints, N7-E production decision; geode: the configured-offset box
 *   grown by one cell) is used; a sample of allowed attempts keeps being verified. The replicated precheck (hybrid) is not part of the production decision.
 * BOX_ONLY (monster room): the replicated precheck was observed to under-estimate vanilla; the box guard stays for the process.
 * ZONE: the footprint bound itself was observed to be wrong, or the vanilla classes differ from the validated ones: every instance whose
 *   3x3-chunk write zone contains a protected piece is cancelled. That holds for ANY behaviour of the vanilla feature, because a feature running in a
 *   WorldGenRegion cannot write outside that zone, so the cancelled set is a superset of every possible collision.
 *
 * Detection before damage: (1) startup fingerprints of the vanilla classes the assumptions depend on; (2) differential verification on allowed
 * attempts that have NO protected piece within the model's reach in the provisional state: a deviation there damages nothing. Only a deviation that
 * first appears after promotion (a model that was right for the calibration sample and wrong later) can be detected after the fact; that residue is
 * limited by the fingerprints and by the continuing sample, and is reported honestly, not claimed as prevented.
 */
public final class DriftGuard {
    public enum Level { PROVISIONAL, VERIFIED, BOX_ONLY, ZONE }

    private static final String P = "net.minecraft.world.level.";
    private static final String FEATURE = P + "levelgen.feature.Feature";
    private static final String STATE_BASE = P + "block.state.BlockBehaviour$BlockStateBase";
    private static final String REGION = "net.minecraft.server.level.WorldGenRegion";
    private static final String START = P + "levelgen.structure.StructureStart";
    /** SHA-256 of the vanilla class files (Minecraft 26.3) this build was validated against. Dependencies: Feature.safeSetBlock decides which writes
     *  happen; BlockStateBase.isSolid is a precheck predicate; BuddingAmethystBlock decides crystal growth; WorldGenRegion bounds writes. */
    static final Map<String, String> KNOWN = Map.of(
            P + "levelgen.feature.MonsterRoomFeature", "006a3287a6b0d65e6e25840f4aea068bd03ce358cfb99e8281f2a55a6529f742",
            P + "levelgen.feature.GeodeFeature", "c1b20c22b95d8bfb43d745c3441ea1b2f15d80bc441c57a5c0f3d18faa556a88",
            FEATURE, "b140a544634d1bc33ccf2cacf00fe0b260652ec52f72ca243f259d3335d43665",
            STATE_BASE, "a712b300de9f9e9bc1a48cdf38c7386ce10bd33bc3dc001861884e6d17029ad1",
            P + "block.BuddingAmethystBlock", "ace9a30177300e5eebaa5799b8b9a356e931ccfab0d08e5af524f968e5a5a175",
            REGION, "f33962d43745ecd21ca163ab713c2af2f8fbcc84b490c285e4b5d8ea0f3b744e",
            START, "0e298de5bc87838033193833366eaca3aef341002686549e060ab532a40736c2");

    public static final class State {
        public final String name;
        final List<String> classes;
        final int needSamples;
        final int needPlacements;
        private volatile Level level = Level.PROVISIONAL;
        private volatile String reason;
        private volatile String fingerprint = "unchecked";
        public final AtomicInteger samples = new AtomicInteger();
        public final AtomicInteger placements = new AtomicInteger();
        public final AtomicInteger deviations = new AtomicInteger();
        public final AtomicInteger nearMisses = new AtomicInteger();
        /** Cancellations taken while not VERIFIED (the cost of not trusting the model yet). */
        public final AtomicInteger unverifiedCancels = new AtomicInteger();
        public volatile long promotedAtAttempt = -1;
        private final AtomicInteger sampleTick = new AtomicInteger();

        State(String name, List<String> classes, int needSamples, int needPlacements) {
            this.name = name;
            this.classes = classes;
            this.needSamples = needSamples;
            this.needPlacements = needPlacements;
        }

        public Level level() {
            return level;
        }

        public String reason() {
            return reason;
        }

        public String fingerprint() {
            return fingerprint;
        }

        /** Every attempt while PROVISIONAL, every 16th once VERIFIED. */
        public boolean shouldSample() {
            return switch (level) {
                case PROVISIONAL -> true;
                case VERIFIED -> sampleTick.incrementAndGet() % 16 == 0;
                default -> false;
            };
        }

        /** Monotone: a level is only ever replaced by a more conservative one. */
        synchronized void demote(Level to, String why) {
            if (to.ordinal() <= level.ordinal()) return;
            level = to;
            reason = why;
            SgProtectionMod.LOGGER.error("SG_PROTECTION drift guard [{}]: {} -> using the {} guard for the rest of this process. Protection stays ON, with more cancellations than necessary."
                    + " Update the module for this Minecraft version.", name, why, to);
        }

        synchronized void promote() {
            if (level != Level.PROVISIONAL) return;
            level = Level.VERIFIED;
            promotedAtAttempt = (name.equals("geode") ? Guard.GEODE : Guard.MONSTER_ROOM).attempts.get();
            SgProtectionMod.LOGGER.info("SG_PROTECTION drift guard [{}]: {} allowed attempts agreed with the model ({} with writes); full decision active", name, samples.get(), placements.get());
        }
    }

    public static final State MONSTER_ROOM = new State("monster_room",
            List.of(P + "levelgen.feature.MonsterRoomFeature", FEATURE, STATE_BASE, REGION, START), 100, 3);
    public static final State GEODE = new State("geode",
            List.of(P + "levelgen.feature.GeodeFeature", FEATURE, P + "block.BuddingAmethystBlock", REGION, START), 3, 3);

    private record Armed(State state, BoundingBox area, BlockState[] before, List<BoundingBox> predicted, BoundingBox hard) {
    }

    private static final ThreadLocal<Armed> ARMED = new ThreadLocal<>();

    private DriftGuard() {
    }

    /**
     * Startup: fingerprint every dependency class and check that nothing else transformed it. Any unknown or unreadable class, or a loaded class that
     * carries methods or interfaces its file does not (what another mod's Mixin adds), puts the feature straight into ZONE: no assumption is trusted.
     * Limit: a transformation that adds no member (an overwrite-style Mixin, a bytecode agent) leaves the class shape unchanged and is not detected here.
     */
    public static void verifyAtStartup() {
        String broken = LabHooks.get().fingerprintBreak();
        for (State s : List.of(MONSTER_ROOM, GEODE)) {
            StringBuilder fp = new StringBuilder();
            String failure = null;
            for (String cls : s.classes) {
                byte[] bytes = read(cls);
                String actual = bytes == null ? null : sha256(bytes);
                fp.append(cls.substring(cls.lastIndexOf('.') + 1)).append('=').append(actual == null ? "unavailable" : actual.substring(0, 12)).append(' ');
                if (actual == null) failure = "cannot read vanilla class " + cls;
                else if (!actual.equals(KNOWN.get(cls))) failure = "vanilla class " + cls + " has fingerprint " + actual + ", validated " + KNOWN.get(cls);
                else {
                    String foreign = foreignMembers(cls, bytes);
                    if (foreign != null) failure = "FOREIGN_TRANSFORM: loaded class " + cls + " carries members that its file does not: " + foreign;
                }
            }
            if (broken != null && (broken.equals("both") || broken.equals(s.name))) failure = "[lab] fingerprint break injected";
            s.fingerprint = fp.toString().trim();
            if (failure != null) s.demote(Level.ZONE, failure.startsWith("FOREIGN") ? failure : "FINGERPRINT_MISMATCH: " + failure);
            else SgProtectionMod.LOGGER.info("SG_PROTECTION drift guard [{}]: vanilla dependency fingerprints validated, no foreign transformer ({}); provisional until verified in-process", s.name, s.fingerprint);
        }
    }

    /** Names of methods or interfaces on the loaded class that the class file does not declare and that are not this module's own; null if none. */
    private static String foreignMembers(String className, byte[] fileBytes) {
        try {
            org.objectweb.asm.tree.ClassNode node = new org.objectweb.asm.tree.ClassNode();
            new org.objectweb.asm.ClassReader(fileBytes).accept(node, org.objectweb.asm.ClassReader.SKIP_CODE);
            java.util.Set<String> fileMethods = new java.util.HashSet<>();
            node.methods.forEach(m -> fileMethods.add(m.name));
            java.util.Set<String> fileInterfaces = new java.util.HashSet<>();
            node.interfaces.forEach(i -> fileInterfaces.add(i.replace('/', '.')));
            Class<?> loaded = Class.forName(className, false, DriftGuard.class.getClassLoader());
            List<String> extra = new ArrayList<>();
            for (java.lang.reflect.Method m : loaded.getDeclaredMethods()) {
                if (!fileMethods.contains(m.getName()) && !ownOrPlatform(m.getName())) extra.add(m.getName());
            }
            for (Class<?> i : loaded.getInterfaces()) {
                if (!fileInterfaces.contains(i.getName()) && !i.equals(GuardMarker.class) && !i.getName().startsWith("net.fabricmc.fabric.")) extra.add("interface " + i.getName());
            }
            return extra.isEmpty() ? null : String.join(", ", extra);
        } catch (ReflectiveOperationException | LinkageError | RuntimeException e) {
            return "(cannot inspect: " + e + ")";
        }
    }

    /**
     * Members that are expected on a loaded vanilla class: this module's own Mixin handlers (named sgprotection$..., possibly wrapped as
     * handler$<id>$<mod>$sgprotection$...) and the members Fabric API itself adds (the platform this module requires; it adds listeners such as
     * BlockStateBase.callUseItemOnEvent, it does not touch the placement logic). Anything else, including a lab mod's inert stand-in, is foreign.
     */
    private static boolean ownOrPlatform(String name) {
        return name.startsWith("sgprotection$") || name.contains("$sgprotection$") || name.startsWith("fabric_api$") || name.matches("handler\\$[^$]*\\$fabric-[^$]*\\$.*");
    }

    private static byte[] read(String className) {
        try (InputStream in = DriftGuard.class.getResourceAsStream("/" + className.replace('.', '/') + ".class")) {
            return in == null ? null : in.readAllBytes();
        } catch (IOException e) {
            return null;
        }
    }

    private static String sha256(byte[] bytes) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        } catch (NoSuchAlgorithmException e) {
            return null;
        }
    }

    /**
     * Monster-room decision in force. ZONE while the footprint bound is unverified (PROVISIONAL) or was observed to be wrong; the configured decision once
     * VERIFIED (the box guard in production; hybrid/precheck exist for the lab only); the box guard for BOX_ONLY (a lab replica was observed to be wrong).
     */
    public static Guard.Refine monsterRoomRefine(Guard.Refine configured) {
        return switch (MONSTER_ROOM.level) {
            case ZONE, PROVISIONAL -> Guard.Refine.ZONE;
            case VERIFIED -> configured;
            case BOX_ONLY -> configured == Guard.Refine.ZONE ? configured : Guard.Refine.OFF;
        };
    }

    /** The 3x3-chunk write zone of the region as a box (full height); null outside world generation. */
    public static BoundingBox zone(WorldGenLevel level) {
        if (!(level instanceof WorldGenRegion region)) return null;
        ChunkPos c = region.getCenter();
        return new BoundingBox((c.x() - 1) * 16, -4096, (c.z() - 1) * 16, (c.x() + 1) * 16 + 15, 4096, (c.z() + 1) * 16 + 15);
    }

    public static boolean isArmed() {
        return ARMED.get() != null;
    }

    public static void discard() {
        ARMED.remove();
    }

    /**
     * Snapshots {@code area} (clipped to the write zone) before vanilla runs. {@code predicted} are the boxes vanilla is believed to write inside,
     * {@code hard} the bound outside which a write is a drift of the footprint itself.
     */
    public static void arm(State s, WorldGenLevel level, BoundingBox area, List<BoundingBox> predicted, BoundingBox hard) {
        BoundingBox zone = zone(level);
        if (zone == null) return;
        int x0 = Math.max(area.minX(), zone.minX());
        int x1 = Math.min(area.maxX(), zone.maxX());
        int y0 = Math.max(area.minY(), level.getMinY());
        int y1 = Math.min(area.maxY(), level.getMaxY());
        int z0 = Math.max(area.minZ(), zone.minZ());
        int z1 = Math.min(area.maxZ(), zone.maxZ());
        if (x0 > x1 || y0 > y1 || z0 > z1) return;
        BoundingBox clipped = new BoundingBox(x0, y0, z0, x1, y1, z1);
        BlockState[] before = new BlockState[(x1 - x0 + 1) * (y1 - y0 + 1) * (z1 - z0 + 1)];
        int i = 0;
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        for (int x = x0; x <= x1; x++) for (int y = y0; y <= y1; y++) for (int z = z0; z <= z1; z++) before[i++] = level.getBlockState(pos.set(x, y, z));
        ARMED.set(new Armed(s, clipped, before, predicted, hard));
    }

    /** After vanilla returned: compare, classify the changes and promote or demote. */
    public static void end(WorldGenLevel level, BlockPos origin) {
        Armed a = ARMED.get();
        if (a == null) return;
        ARMED.remove();
        BoundingBox b = a.area();
        int changed = 0;
        int outsidePredicted = 0;
        int outsideHard = 0;
        int i = 0;
        BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
        for (int x = b.minX(); x <= b.maxX(); x++) {
            for (int y = b.minY(); y <= b.maxY(); y++) {
                for (int z = b.minZ(); z <= b.maxZ(); z++) {
                    if (a.before()[i++] == level.getBlockState(pos.set(x, y, z))) continue;
                    changed++;
                    boolean inPredicted = false;
                    for (BoundingBox p : a.predicted()) {
                        if (p.isInside(x, y, z)) {
                            inPredicted = true;
                            break;
                        }
                    }
                    if (!inPredicted) outsidePredicted++;
                    if (!a.hard().isInside(x, y, z)) outsideHard++;
                }
            }
        }
        State s = a.state();
        if (outsideHard > 0) {
            s.deviations.incrementAndGet();
            s.demote(Level.ZONE, "RUNTIME_DEVIATION: " + s.name + " at " + origin + " changed " + outsideHard + " cell(s) outside its footprint bound");
        } else if (outsidePredicted > 0) {
            s.deviations.incrementAndGet();
            s.demote(Level.BOX_ONLY, "RUNTIME_DEVIATION: " + s.name + " at " + origin + " changed " + outsidePredicted + " cell(s) its precheck model said it would not write");
        } else {
            s.samples.incrementAndGet();
            if (changed > 0) s.placements.incrementAndGet();
            if (s.level == Level.PROVISIONAL && s.samples.get() >= s.needSamples && s.placements.get() >= s.needPlacements) s.promote();
        }
    }
}
