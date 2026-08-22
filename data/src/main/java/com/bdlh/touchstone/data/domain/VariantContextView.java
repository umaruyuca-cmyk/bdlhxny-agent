package com.bdlh.touchstone.data.domain;

import java.util.List;

/** 变体上下文条目目录:引擎压缩对照执行的输入真源。 */
public record VariantContextView(
        String caseId,
        int caseVersion,
        String variantId,
        String contextStrategy,
        int tokenBudget,
        /** fixture_context_items(正规表)或 case_variants.data_fixture(JSONB 兼容) */
        String source,
        List<VariantContextItem> items) {

    public record VariantContextItem(
            String itemKey,
            String itemType,
            String classification,
            String content,
            int priority,
            boolean trusted,
            int sequence,
            boolean untrusted,
            boolean stale,
            String validFrom,
            String validTo,
            boolean crossUser,
            String duplicateOf,
            String observedAt) {}
}
