package dev.itzgamesgd.sg01spike.mixin;

import java.util.List;
import java.util.Set;
import org.objectweb.asm.tree.ClassNode;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;

/**
 * Keeps the observe-only measurement mixins (the "*ProbeMixin" classes) out of production: they are applied only when the validation lab sets
 * SG01_LAB=1. The two protection hooks (GeodeFeatureMixin, MonsterRoomFeatureMixin) are always applied and stay fail-loud.
 */
public final class SgMixinPlugin implements IMixinConfigPlugin {
    private static final boolean LAB = "1".equals(System.getenv("SG01_LAB")) || "1".equals(System.getProperty("sg01.lab"));

    @Override
    public void onLoad(String mixinPackage) {
    }

    @Override
    public String getRefMapperConfig() {
        return null;
    }

    @Override
    public boolean shouldApplyMixin(String targetClassName, String mixinClassName) {
        return LAB || !mixinClassName.endsWith("ProbeMixin");
    }

    @Override
    public void acceptTargets(Set<String> myTargets, Set<String> otherTargets) {
    }

    @Override
    public List<String> getMixins() {
        return null;
    }

    @Override
    public void preApply(String targetClassName, ClassNode targetClass, String mixinClassName, IMixinInfo mixinInfo) {
    }

    @Override
    public void postApply(String targetClassName, ClassNode targetClass, String mixinClassName, IMixinInfo mixinInfo) {
    }
}
