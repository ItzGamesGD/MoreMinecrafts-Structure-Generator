package dev.itzgamesgd.sg01spike;

import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.feature.MonsterRoomFeature;
import net.minecraft.world.level.levelgen.structure.BoundingBox;

/**
 * Runtime compatibility self-check for the hybrid monster-room decision (N7-B). The hybrid decision is only sound while vanilla's
 * {@code MonsterRoomFeature.place} still behaves as {@link MonsterRoomGeometry} replicates it (footprint bounds and read-only precheck).
 * Two independent checks establish that, and when either cannot, the guard falls back, for the rest of the process, to the conservative box
 * guard (the N7-A reach: the union of all variant footprints), never to "off":
 *
 * 1. Startup fingerprint: the SHA-256 of the vanilla {@code MonsterRoomFeature} class file must be one this build was validated against.
 *    An unreadable class or an unknown fingerprint means vanilla changed (or cannot be inspected), so the replication is not established.
 * 2. Runtime near-miss watch: whenever the hybrid decision lets vanilla run although a protected piece lies inside the widest possible footprint,
 *    the cells of that overlap are snapshotted and compared after vanilla returns. Any change is a direct violation of the invariant
 *    "an attempt the refined decision allows writes nothing into a protected piece" and triggers the fallback at once.
 *
 * The watch detects a violation after the fact (that one placement already happened); the fingerprint is what prevents it up front.
 */
public final class MonsterRoomSelfCheck {
    private static final String CLASS_RESOURCE = "/net/minecraft/world/level/levelgen/feature/MonsterRoomFeature.class";
    /** SHA-256 values of the MonsterRoomFeature class file of the Minecraft versions this build was validated against (26.3). */
    static final Set<String> KNOWN_FINGERPRINTS = Set.of("006a3287a6b0d65e6e25840f4aea068bd03ce358cfb99e8281f2a55a6529f742");

    private static volatile String fallbackReason;
    private static volatile String fingerprint = "unchecked";
    public static final AtomicInteger NEAR_MISSES = new AtomicInteger();
    public static final AtomicInteger VIOLATIONS = new AtomicInteger();

    private record Watch(List<BoundingBox> cells, List<BlockState> before) {
    }

    private static final ThreadLocal<Watch> WATCH = new ThreadLocal<>();

    private MonsterRoomSelfCheck() {
    }

    /** Establishes the startup fingerprint. Never throws: failure to establish compatibility selects the fallback. */
    public static void verifyAtStartup() {
        String expectedOverride = Guard.LAB ? System.getenv("SG01_LAB_MR_FINGERPRINT") : null;
        String actual;
        try (InputStream in = MonsterRoomFeature.class.getResourceAsStream(CLASS_RESOURCE)) {
            if (in == null) throw new IOException("class resource not found");
            actual = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(in.readAllBytes()));
        } catch (IOException | NoSuchAlgorithmException e) {
            fingerprint = "unavailable";
            fallback("FINGERPRINT_UNAVAILABLE: cannot read the vanilla MonsterRoomFeature class (" + e.getMessage() + ")");
            return;
        }
        fingerprint = actual;
        Set<String> accepted = expectedOverride != null && !expectedOverride.isBlank() ? Set.of(expectedOverride.trim()) : KNOWN_FINGERPRINTS;
        if (accepted.contains(actual)) {
            SpikeMod.LOGGER.info("SG_SPIKE monster-room self-check: vanilla MonsterRoomFeature fingerprint {} is validated; hybrid decision active", actual);
        } else {
            fallback("FINGERPRINT_MISMATCH: vanilla MonsterRoomFeature fingerprint " + actual + " is not one this build was validated against " + accepted);
        }
    }

    /** The decision actually in force: the configured one, unless the self-check selected the conservative box guard. */
    public static Guard.Refine effective(Guard.Refine configured) {
        return fallbackReason != null && configured != Guard.Refine.OFF ? Guard.Refine.OFF : configured;
    }

    public static boolean inFallback() {
        return fallbackReason != null;
    }

    public static String fallbackReason() {
        return fallbackReason;
    }

    public static String fingerprint() {
        return fingerprint;
    }

    private static synchronized void fallback(String reason) {
        if (fallbackReason != null) return;
        fallbackReason = reason;
        SpikeMod.LOGGER.error("SG_SPIKE monster-room self-check FAILED ({}); falling back to the conservative box guard for the rest of this process."
                + " Protection stays ON, with more cancellations than necessary. Update the module for this Minecraft version.", reason);
    }

    /** Called when the hybrid decision allows vanilla although protected pieces overlap the widest footprint {@code broad}. */
    public static void begin(WorldGenLevel level, BoundingBox broad, List<BoundingBox> pieces) {
        NEAR_MISSES.incrementAndGet();
        List<BoundingBox> cells = new ArrayList<>();
        List<BlockState> before = new ArrayList<>();
        for (BoundingBox piece : pieces) {
            int x0 = Math.max(piece.minX(), broad.minX());
            int x1 = Math.min(piece.maxX(), broad.maxX());
            int y0 = Math.max(piece.minY(), broad.minY());
            int y1 = Math.min(piece.maxY(), broad.maxY());
            int z0 = Math.max(piece.minZ(), broad.minZ());
            int z1 = Math.min(piece.maxZ(), broad.maxZ());
            if (x0 > x1 || y0 > y1 || z0 > z1) continue;
            BoundingBox overlap = new BoundingBox(x0, y0, z0, x1, y1, z1);
            cells.add(overlap);
            for (BlockPos pos : BlockPos.betweenClosed(x0, y0, z0, x1, y1, z1)) before.add(level.getBlockState(pos));
        }
        WATCH.set(new Watch(cells, before));
    }

    public static void discard() {
        WATCH.remove();
    }

    /** Called after vanilla returned: any difference in a watched overlap is a violation. */
    public static void end(WorldGenLevel level, BlockPos origin) {
        Watch watch = WATCH.get();
        if (watch == null) return;
        WATCH.remove();
        int index = 0;
        int changed = 0;
        for (BoundingBox box : watch.cells()) {
            for (BlockPos pos : BlockPos.betweenClosed(box.minX(), box.minY(), box.minZ(), box.maxX(), box.maxY(), box.maxZ())) {
                if (watch.before().get(index++) != level.getBlockState(pos)) changed++;
            }
        }
        if (changed > 0) {
            VIOLATIONS.incrementAndGet();
            fallback("RUNTIME_VIOLATION: vanilla monster room at " + origin + " changed " + changed + " cell(s) of a protected piece in an attempt the hybrid decision had allowed");
        }
    }
}
