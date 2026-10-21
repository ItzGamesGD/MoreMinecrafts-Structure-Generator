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
    /** ORACLE confusion matrix: decision (cancel?) of the REFINED guard vs. whether vanilla changed a block inside a protected piece box. */
    public final AtomicLong refinedTp = new AtomicLong();
    public final AtomicLong refinedFp = new AtomicLong();
    public final AtomicLong refinedFn = new AtomicLong();
    public final AtomicLong refinedTn = new AtomicLong();
    /** Same matrix for the N7-A reach box. */
    public final AtomicLong n7aTp = new AtomicLong();
    public final AtomicLong n7aFp = new AtomicLong();
    public final AtomicLong n7aFn = new AtomicLong();
    public final AtomicLong n7aTn = new AtomicLong();
    /** HYBRID: broad-phase said no protected piece can be reached, so the narrow precheck was never run. */
    public final AtomicLong hybridSkip = new AtomicLong();
    /** SHADOW (HYBRID only): the broad-phase decision was compared with the refined decision. */
    public final AtomicLong shadowChecks = new AtomicLong();
    /** SHADOW: broad-phase said no, but the refined decision would cancel. Must stay 0. */
    public final AtomicLong shadowViolations = new AtomicLong();
    private final List<String> events = new ArrayList<>();

    GuardStats(String feature) {
        this.feature = feature;
    }

    public synchronized void event(String line) {
        if (events.size() < 400) events.add(line);
    }

    public synchronized int eventCount() {
        return events.size();
    }

    synchronized List<String> events() {
        return new ArrayList<>(events);
    }
}
