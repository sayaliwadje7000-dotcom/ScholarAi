    def aggregate(
        self,
        candidate: HybridCandidate,
        normalized_scores: tuple[
            NormalizedComponentScore,
            ...,
        ],
    ) -> HybridScoreResult:
        if not isinstance(candidate, HybridCandidate):
            raise HybridAggregationError(
                "candidate must be a HybridCandidate."
            )

        if not isinstance(normalized_scores, tuple):
            raise HybridAggregationError(
                "normalized_scores must be a tuple."
            )

        normalized_by_component: dict[
            RecommendationComponent,
            NormalizedComponentScore,
        ] = {}

        for score in normalized_scores:
            if not isinstance(score, NormalizedComponentScore):
                raise HybridAggregationError(
                    "Invalid normalized score object."
                )

            if not isinstance(
                score.component,
                RecommendationComponent,
            ):
                raise HybridAggregationError(
                    "Normalized score has an invalid component."
                )

            if score.component in normalized_by_component:
                raise HybridAggregationError(
                    "Duplicate normalized component score."
                )

            normalized_by_component[score.component] = score

        candidate_available = {
            item.component
            for item in candidate.component_scores
            if item.status == ComponentStatus.AVAILABLE
        }

        positive_weight_components = {
            component
            for component, weight in self._weight_config.weights.items()
            if weight > 0.0
        }

        expected_components = (
            candidate_available & positive_weight_components
        )

        if set(normalized_by_component) != expected_components:
            raise HybridAggregationError(
                "Normalized scores must match all and only "
                "available candidate components with positive "
                "configured weights."
            )

        if not expected_components:
            raise HybridAggregationError(
                "No available component has a positive configured weight."
            )

        configured_weight_total = sum(
            self._weight_config.weights[component]
            for component in expected_components
        )

        if (
            not isfinite(configured_weight_total)
            or configured_weight_total <= 0.0
        ):
            raise HybridAggregationError(
                "Configured weight total must be finite and positive."
            )

        contributions: list[ComponentContribution] = []
        hybrid_score = 0.0

        ordered_components = sorted(
            expected_components,
            key=lambda component: component.value,
        )

        for component in ordered_components:
            normalized = normalized_by_component[component]
            configured_weight = self._weight_config.weights[component]

            effective_weight = (
                configured_weight / configured_weight_total
            )

            weighted_contribution = (
                normalized.normalized_score * effective_weight
            )

            hybrid_score += weighted_contribution

            contributions.append(
                ComponentContribution(
                    component=component,
                    normalized_score=normalized.normalized_score,
                    configured_weight=configured_weight,
                    effective_weight=effective_weight,
                    weighted_contribution=weighted_contribution,
                )
            )

        excluded_components = tuple(
            sorted(
                (
                    item.component
                    for item in candidate.component_scores
                    if item.component not in expected_components
                ),
                key=lambda component: component.value,
            )
        )

        return HybridScoreResult(
            resource_id=candidate.resource_id,
            hybrid_score=hybrid_score,
            normalized_scores=tuple(
                normalized_by_component[component]
                for component in ordered_components
            ),
            contributions=tuple(contributions),
            available_components=tuple(ordered_components),
            excluded_components=excluded_components,
            configured_weight_total=configured_weight_total,
            effective_weight_total=sum(
                contribution.effective_weight
                for contribution in contributions
            ),
        )