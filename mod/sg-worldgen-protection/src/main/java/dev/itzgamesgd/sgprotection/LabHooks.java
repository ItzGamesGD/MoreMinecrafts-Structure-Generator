package dev.itzgamesgd.sgprotection;

import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.levelgen.structure.BoundingBox;

/**
 * The only seam between the production guard and the validation lab (N7-D). The production artifact reads no configuration from the environment and
 * contains no instrumentation; a separate lab mod (jar {@code sg-worldgen-protection-lab}, never shipped) may register an implementation through the
 * {@code sg_worldgen_protection:lab} entrypoint to change the configuration, observe, inject faults and add report sections. Without it every method
 * is the no-op below and {@link #config()} is the production configuration.
 */
public interface LabHooks {
    /** Guard configuration. The production values are the defaults in {@link #DEFAULT}: ENFORCE, the conservative box guard for the monster room (Refine.OFF). */
    record Config(Guard.Mode mode, Guard.Refine refine, String features, Guard.Fixture fixture, Guard.Fault fault, boolean shadow, boolean oracle) {
    }

    Config DEFAULT = new Config(Guard.Mode.ENFORCE, Guard.Refine.OFF, "both", Guard.Fixture.NONE, Guard.Fault.NONE, false, false);
    LabHooks NONE = new LabHooks() {
    };

    /** Installed once, from SgProtectionMod.onInitialize, before any guard decision. */
    final class Holder {
        static volatile LabHooks current = NONE;

        private Holder() {
        }
    }

    static LabHooks get() {
        return Holder.current;
    }

    static void install(LabHooks hooks) {
        Holder.current = hooks;
    }

    default Config config() {
        return DEFAULT;
    }

    /** Scope of a guard decision (read accounting). */
    default void enter() {
    }

    default void exit() {
    }

    /** Timing of one hooked feature call: mark at the start, decision done, place done (vanillaRan: the feature body ran). */
    default void mark() {
    }

    default void decisionDone(boolean geode) {
    }

    default void placeDone(boolean geode, boolean vanillaRan) {
    }

    default void oracleBegin(GuardStats stats, WorldGenLevel level, BlockPos origin, List<BoundingBox> refined) {
    }

    default void oracleEnd(GuardStats stats, WorldGenLevel level, BlockPos origin) {
    }

    /** Lab only: "monster_room", "geode" or "both" makes the vanilla class fingerprints of that feature count as mismatching. */
    default String fingerprintBreak() {
        return null;
    }

    /** Lab only: a cancellation was taken while the feature was not VERIFIED; {@code verifiedReach} is the geode reach (null for the monster room). */
    default void unverifiedCancel(boolean geode, WorldGenLevel level, BlockPos origin, BoundingBox verifiedReach) {
    }

    /** Lab only: adversarial probe of the write-zone boundary, called at the start of a monster-room attempt while Fault.ZONE_PROBE is active. */
    default void zoneProbe(WorldGenLevel level, BlockPos origin) {
    }

    /** Extra report members, each prefixed by a comma, for example {@code ,"probe":{...}}. */
    default String reportExtras() {
        return "";
    }

    default void serverStarted(MinecraftServer server) {
    }

    default void serverStopping() {
    }
}
