package dev.itzgamesgd.sg01spike;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/** Counters and a bounded event log for one guarded feature class. */
public final class GuardStats {
    public final String feature;
    public final AtomicLong attempts = new AtomicLong();
    /** No protected structure reference in the touched chunks: vanilla path, no further work. */
    public final AtomicLong fastPath = new AtomicLong();
    /** Reach box intersected a protected piece. */
    public final AtomicLong collisions = new AtomicLong();
    /** Required structure data could not be read: safe cancellation decision. */
    public final AtomicLong unavailable = new AtomicLong();
    /** Instances actually cancelled (enforce mode only). */
    public final AtomicLong cancelled = new AtomicLong();
    /** Instances that would have been cancelled (observe mode). */
    public final AtomicLong wouldCancel = new AtomicLong();
    /** Reference present, no collision, no unavailable data: the decision is "not protected". */
    public final AtomicLong clear = new AtomicLong();
    /** Calls whose level was not a WorldGenRegion (commands, other mods): untouched. */
    public final AtomicLong notWorldgen = new AtomicLong();
    /** REFINE=precheck: vanilla's own read-only precheck fails for every variant, so vanilla writes nothing and no decision is needed. */
    public final AtomicLong noWrite = new AtomicLong();
    /** ORACLE: vanilla ran unguarded and changed a non-air block inside a protected piece box. */
    public final AtomicLong oracleNonAirWrite = new AtomicLong();
    /** ORACLE: vanilla ran unguarded and changed no non-air block inside a protected piece box. */
    public final AtomicLong oracleNoWrite = new AtomicLong();
    /** ORACLE: piece boxes could not be read, so the attempt is unclassified. */
    public final AtomicLong oracleUnknown = new AtomicLong();
    private final List<String> events = new ArrayList<>();

    GuardStats(String feature) {
        this.feature = feature;
    }

    synchronized void event(String line) {
        if (events.size() < 400) events.add(line);
    }

    synchronized List<String> events() {
        return new ArrayList<>(events);
    }
}
