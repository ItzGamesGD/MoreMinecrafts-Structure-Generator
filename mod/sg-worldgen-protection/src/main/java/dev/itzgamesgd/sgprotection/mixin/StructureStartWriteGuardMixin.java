package dev.itzgamesgd.sgprotection.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import dev.itzgamesgd.sgprotection.WriteGuard;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import org.spongepowered.asm.mixin.Mixin;

/** Marks the placement of a protected structure's own start, so that only its own writes are exempt from the write guard (exception-safe). */
@Mixin(StructureStart.class)
public abstract class StructureStartWriteGuardMixin {
    @WrapMethod(method = "placeInChunk", require = 1)
    private void sgprotection$wrapPlace(WorldGenLevel level, StructureManager structures, ChunkGenerator generator, RandomSource random, BoundingBox box, ChunkPos chunk,
                                        Operation<Void> original) {
        StructureStart self = (StructureStart) (Object) this;
        WriteGuard.enterPlacement(self.getStructure());
        try {
            original.call(level, structures, generator, random, box, chunk);
        } finally {
            WriteGuard.exitPlacement(self.getStructure());
        }
    }
}
