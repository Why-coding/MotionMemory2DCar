# Merge Lane and Lane Intent Closeout Brief

**One-line status:** The system can execute smooth, adjacent, physically bounded merge trajectories, and an experimental PPO policy can merge perfectly in certified-safe states; however, no learned checkpoint yet selects **merge now versus keep waiting** safely and consistently across the general safe/unsafe boundary, so learned lane changing is not in production.

## 1. Executive Summary

The lane project has solved the **road representation and maneuver execution** problem, and it has partially solved the **learned decision** problem.

What is proven:

- Roads can be represented as connected lane segments with stable IDs.
- Lanes can appear, terminate, and have station-dependent neighbors.
- A vehicle can move continuously from an ending auxiliary lane into an adjacent continuing lane.
- The merge trajectory respects adjacency, continuity, lateral-acceleration, and lateral-jerk limits.
- Collision checks account for a vehicle overlapping both lanes during a maneuver.
- The policy receives the relevant target-lane gap, relative-speed, TTC, lane-end, and route-progress information.
- A PPO-trained experimental checkpoint learned to select LEFT with 100% completion and zero safety events on a fully certified safe-acquisition distribution.

What is not yet proven:

- General safe/unsafe merge-boundary selection.
- Dynamic gap preparation or learned longitudinal negotiation during a merge.
- General left and right lane changing on arbitrary roads.
- Multi-step destination lane planning.
- Learned use of the left-turn pocket.
- Production integration of the segment topology or V6 lane-intent policy.

Production remains:

```text
Checkpoint: yield_kinodynamic_v5_combined_production.npz
Topology: legacy_path_v1
Learned merge/lane-change claim: none
```

The strongest experimental partial artifact is:

```text
Checkpoint: yield_kinodynamic_v6_merge_stage4_7_phase1_main_update_2.npz
SHA-256: dd3a432511cfac9517125a56a19d8344a7803de502e3006923ba443d6b4f8d26
Scope: certified-safe LEFT acquisition only
Production status: rejected outside that limited scope
```

## 2. What Has Been Implemented?

### 2.1 Lane topology

The experimental environment contains a lane-segment graph rather than only fixed intersection paths.

Implemented capabilities:

- `LaneSegment` objects with stable segment IDs.
- Explicit predecessor and successor relationships.
- Station-dependent left and right adjacency.
- Lane birth and lane termination.
- A two-lane straight layout with one ending auxiliary merge lane.
- Continuous route progress across connected segments.
- Adjacent-only transitions; no direct multi-lane jumps.
- An auxiliary left-turn-pocket topology with receiving-lane connectivity.

This layer answers: **Where can a vehicle legally travel?**

It does not answer: **When should the vehicle change lanes?** That is the policy's task.

### 2.2 Lane-change trajectory execution

Once a lane intent is committed, a deterministic trajectory generator creates a smooth path into the adjacent lane.

Implemented safeguards and measurements:

- Continuous lateral interpolation.
- No teleportation between lane centers.
- Bounded maneuver duration.
- Lane-change commitment and completion state.
- Bounded abort semantics before commitment.
- No arbitrary abort after the maneuver becomes physically committed.
- Lateral acceleration and jerk measurements.
- Oriented-polygon collision checking during partial overlap.

Measured scripted-regression peaks are approximately:

```text
Peak lateral acceleration: 1.059 m/s^2
Peak lateral jerk:         2.500 m/s^3
```

This layer is deterministic because continuous trajectory generation and physical comfort are low-level control responsibilities. PPO is intended to learn the high-level decision, not rediscover basic spline geometry through collisions.

### 2.3 Merge observations

The experimental V6 policy receives a 24-value lane context containing:

1. Current and target segment types.
2. Left and right topology validity.
3. Distance to the end of the current lane.
4. Taper distance.
5. Lane-change progress and commitment.
6. Target-lane front gap.
7. Target-lane rear gap.
8. Front and rear closing speeds.
9. Front and rear TTC.
10. Expected target-follower braking.
11. Ego speed.
12. Target-lane mean speed.
13. Remaining lateral offset.
14. Whether a merge is required.
15. Continuous route progress.

The Stage 4.1 observability audit confirmed that the inputs used by the diagnostic merge oracle are represented in the policy context. There was no confirmed hidden oracle input missing from the observation.

### 2.4 Lane-intent policy

The V6 experimental architecture adds three high-level categorical options:

```text
KEEP  = remain on the current lane segment
LEFT  = begin or continue a valid adjacent-left maneuver
RIGHT = begin or continue a valid adjacent-right maneuver
```

It contains:

- A lane-context encoder.
- A categorical lane-intent head.
- A lane-option critic.
- A persistent-option controller.
- A merge-acceleration residual head, currently fixed at zero in the accepted partial work.

The production V5 longitudinal actor remains frozen and supplies longitudinal driving behavior. During accepted lane-intent experiments, PPO changed only the lane encoder, lane-intent head, and option critic.

### 2.5 Persistent intent

Lane intent is treated as a semi-Markov option rather than resampled every 0.2-second physics tick.

- `KEEP` persists for the configured option interval, currently 1.0 simulation second.
- `LEFT` or `RIGHT` persists through a committed maneuver.
- A new high-level choice is made only at a valid option boundary.
- Longitudinal control is still evaluated every 0.2 seconds.

This prevents LEFT/KEEP oscillation during one physical lane change and aligns one high-level decision with one meaningful maneuver segment.

### 2.6 Merge oracle and certification harness

A deterministic merge-gap oracle evaluates:

- Target front and rear gaps.
- Relative speeds.
- Front and rear TTC.
- Expected braking imposed on the target follower.
- Remaining lane-end distance.
- Maneuver duration.

The oracle is used only for:

- Constructing diagnostic scenarios.
- Certifying whether a state is physically safe or unsafe.
- Building evaluation baselines.
- Performing copied-state counterfactual analysis.

It is not used as a runtime safety shield in accepted experiments, and it does not replace PPO actions.

## 3. What Is the Policy Trying to Learn?

The main learned decision is:

> Given the current lane-end distance, target-lane gaps, relative motion, and route need, should the vehicle merge now or keep its current lane for another option interval?

The policy is not being asked to learn road connectivity or draw a physically smooth curve. It is learning the behaviorally meaningful decision boundary.

### LEFT_REQUIRED_NOW

Immediate LEFT is preferred because delaying one option interval closes the opportunity, makes the maneuver infeasible, causes lane-end failure, or materially worsens the route outcome.

Example: a safe gap exists now, the auxiliary lane is ending, and the gap will close before the next decision.

### KEEP_REQUIRED_NOW

Immediate LEFT is unsafe or materially worse, while KEEP avoids the adverse outcome.

Example: a fast rear vehicle in the target lane would require hard braking or collide if ego merged now.

### FLEXIBLE

Both immediate LEFT and one interval of KEEP remain safe and preserve a successful route outcome.

Example: the target lane has a large stable gap and the ego still has enough lane distance to merge at the next option event.

### INCONCLUSIVE

No stable immediate preference can be established, both branches fail similarly, or the result depends on the bounded continuation policy.

Only `LEFT_REQUIRED_NOW` and `KEEP_REQUIRED_NOW` belong in the primary decisive PPO bank. FLEXIBLE states are retained for regression testing but should not be assigned an artificial correct action.

## 4. What Will the Policy Be Able to Do After Learning?

After the static and dynamic merge stages pass, the intended behavior is:

1. Detect that its current lane terminates or is inconsistent with the route.
2. Observe adjacent-lane topology and target-lane traffic.
3. Distinguish a currently safe gap from a gap that is unsafe or closing.
4. Merge promptly when waiting would lose the opportunity.
5. Wait when a merge would cut off a front or rear vehicle.
6. Reassess at the next valid decision event.
7. Commit once the maneuver has progressed too far to abort safely.
8. Follow a smooth trajectory without teleporting or jumping lanes.
9. Complete the merge without excessive lateral acceleration or jerk.
10. Preserve established longitudinal yielding, signals, pedestrians, and queue behavior.

Later work can extend the same mechanism to:

- Rightward lane changes.
- Multiple adjacent lane changes performed one at a time.
- Destination-oriented lane selection.
- Entering a left-turn pocket before an intersection.
- Changing lanes after a turn to reach a destination lane.

Those later claims depend on first solving the current LEFT-versus-KEEP boundary.

## 5. Current Issues

### 5.1 No production learned-lane checkpoint

Production V5 does not use segment topology or learned lane intent. Every V6 merge candidate remains experimental.

### 5.2 Safe acquisition was learned, but the safety boundary was not

Stage 4.7 update 2 learned the certified-safe acquisition task:

```text
Safe-bank completion:       100%
Safe-opportunity acceptance: 100%
Collision events:             0
Unsafe entries:               0
```

But outside that narrow scope it selected LEFT almost everywhere:

```text
Static-bank unsafe-entry rate: 34.783%
Static-bank collision rate:    11.719%
Deterministic LEFT / KEEP:     128 / 0
```

This is a learned safe-action capability, not a learned safe/unsafe boundary.

### 5.3 The corrected boundary candidate still failed its gate

Stage 4.8R update 1 achieved:

```text
Physical preference accuracy: 91.960%
LEFT-required completion:      100%
LEFT-required collisions:        0
KEEP rate in unsafe states:     91.213%
Unsafe-entry rate:               8.787%
Required unsafe-entry gate:     <=5%
```

It was close but not safe enough. Update 2 then shifted too far toward KEEP and fell to 68.467% aggregate preference accuracy.

### 5.4 Dynamic merge preparation has not started

The accepted partial work keeps the merge-acceleration residual exactly zero. The policy has not yet learned to:

- Adjust speed to create a future gap.
- Coordinate with a target-lane follower.
- Prepare early for a narrowing lane.
- Negotiate stop-and-go traffic during a merge.

Dynamic-gap PPO was intentionally deferred until the static LEFT/KEEP boundary passes.

### 5.5 General lane changing is still later scope

The current learned bank uses an ending right-side auxiliary lane whose valid escape is LEFT. Therefore RIGHT is topologically invalid and masked in these scenarios.

The architecture supports RIGHT, but rightward and multi-step lane-change distributions have not been trained or qualified.

## 6. Why Did These Issues Occur?

The current problem is the result of several distinct methodology issues discovered sequentially.

### 6.1 Offline learning did not transfer to integrated rollouts

The earliest merge experiments used balanced oracle prewarm. The lane head saw equal LEFT/KEEP labels offline, but the integrated policy mostly selected KEEP and rarely visited the states needed to improve.

Stage 4.1 reached good offline classification but only 43.17% integrated required-merge completion, with 17.36% unsafe merges.

Lesson: offline classification accuracy is not evidence that the closed-loop policy can safely act under its own state distribution.

### 6.2 The original reward ordering was wrong

In blocked cases, unsafe LEFT could receive more return than safe KEEP. Stage 4.2 introduced versioned `merge_reward_v2` with the intended hierarchy:

```text
safe successful merge
> safe waiting with no feasible gap
> safe route miss
> missed required opportunity
> unsafe forced merge
> collision
```

This fixed the reward-ordering defect, but PPO still produced approximately 22-24% unsafe entries. Reward correctness was necessary but not sufficient.

### 6.3 Exploration and safety opposed each other

A state-independent LEFT prior could not satisfy both requirements:

- Low LEFT probability: safe, but almost no LEFT experience.
- Higher LEFT probability: enough exploration, but unsafe entries increased sharply.

Stage 4.5 used a 2% LEFT prior and needed 10,439 environment steps to obtain only 32 natural LEFT decisions. Many occurred late or in unsafe states, so their negative return correctly pushed the policy toward KEEP.

### 6.4 Per-tick decisions produced poor temporal credit

Originally, lane intent was resampled every physics tick. Unsafe choices generated repeated negative samples, while successful completion produced sparse delayed credit.

Stage 4.4 therefore:

- Corrected a rollout truncation/bootstrap defect.
- Added persistent high-level options.
- Implemented semi-Markov rewards and `gamma^k` bootstrapping.
- Separated lane-option PPO from residual PPO.

This made the mathematical unit of learning correspond to the physical unit of behavior.

### 6.5 The curriculum initially contained the wrong LEFT samples

The Stage 4.5 reconstruction classified its 36 sampled LEFT decisions as:

```text
Feasible safe LEFT:             11
Insufficient maneuver distance:  8
Too late for completion:         3
Unsafe gap at decision:         14
```

The negative LEFT learning signal was therefore physically justified. Stage 4.6 replaced these states with offline-certified early safe windows.

### 6.6 “LEFT eventually succeeds” was confused with “LEFT is required now”

Stage 4.8 originally classified preference by comparing forced LEFT until outcome with forced KEEP until lane failure. That answered a route-level question, not the immediate one-option decision.

Stage 4.8R copied the exact simulator and RNG state and compared:

- `LEFT_NOW`: one LEFT option, then fixed continuation.
- `KEEP_NOW`: one KEEP option, then the identical continuation.
- Forced LEFT to outcome.
- Forced KEEP to outcome.

The audit found:

```text
Original safe states classified FLEXIBLE:     2,553
Original safe states classified INCONCLUSIVE:     7
Original unsafe states KEEP_REQUIRED_NOW:      2,560
Forced-vs-one-option ordering disagreements:     747
```

The original safe bank was mostly not an immediate LEFT-required bank.

### 6.7 Completion credit often arrived after the initiating LEFT option

The `+30` safe-completion bonus generally occurred after the initial LEFT option had closed and was owned by a later option. This was confirmed as a secondary credit-timing issue.

It was not changed because the primary defect was the preference definition. The project followed the rule of making only the smallest correction justified by the audit.

### 6.8 The remaining defect is in actor-gradient aggregation

After rebuilding a truly decisive bank, exact paired Monte Carlo and GAE checks favored the physically correct actions. Before the blocked Stage 4.8R third update:

```text
LEFT-required raw GAE, LEFT action: 0.938450
LEFT-required raw GAE, KEEP action: 0.172665
Predicted LEFT-minus-KEEP gradient: -0.003315
```

The better action had the better return, but the aggregate actor gradient would still reduce LEFT preference.

That points to the PPO actor aggregation path, including:

- Action-probability weighting.
- Likelihood ratios.
- PPO clipping.
- Unequal sampled action counts.
- Shared lane-encoder gradients.
- Interaction between LEFT-required and KEEP-required samples.

The exact responsible term has not yet been isolated. Therefore the correct next action is a frozen-buffer gradient decomposition, not blind additional PPO or another reward rewrite.

## 7. Changes Made and the Reasoning Behind Them

| Change | Why it was needed | Result |
|---|---|---|
| Segment-graph lane model | Fixed paths cannot represent lane birth, termination, or changing adjacency | Topology and continuity tests pass |
| Stable lane IDs | Prevent identity changes across connected segments | Deterministic routing and reproducible traces |
| Adjacent-only transitions | Prevent teleportation and multi-lane jumps | Zero invalid jumps in accepted tests |
| Smooth deterministic trajectory | Separate maneuver geometry from behavioral intent | Comfort and continuity pass |
| Oriented collision polygons | Center-distance checks miss partial-overlap collisions | Overlap collisions detected correctly |
| 24-feature lane context | Expose the variables needed for gap acceptance | Oracle-input observability confirmed |
| Categorical lane-intent head | Steering scalar was not a reliable discrete lane-selection interface | Explicit KEEP/LEFT/RIGHT probabilities |
| Separate lane-option critic | Lane decisions occur at a different timescale from acceleration | Option-level value and GAE diagnostics |
| Persistent-option controller | Per-tick resampling caused chatter and repeated credit | One intent spans one meaningful maneuver interval |
| Truncation/bootstrap correction | Rollout boundaries were treated as terminal | Correct semi-Markov GAE propagation |
| `merge_reward_v2` | Original reward could prefer unsafe LEFT over safe KEEP | Counterfactual reward hierarchy passes |
| Physically certified curriculum | Random LEFT samples were mostly late or unsafe | Stage 4.7 learned safe acquisition |
| Exact copied-state counterfactuals | Forced-to-outcome labels did not identify immediate preference | FLEXIBLE states and true decisive states separated |
| Hard pre-update gradient gates | Prevent optimizer updates when the measured direction contradicts physics | Unsafe updates 3 were blocked |
| Frozen V5 actor and zero residual | Isolate the lane-decision problem from longitudinal-policy changes | Clear attribution of every result |

## 8. Current Methodology Verdict

The work has demonstrated three increasingly strong claims:

1. **Scripted feasibility:** The topology and trajectory can execute safe merges.
2. **Learned safe acquisition:** PPO can learn LEFT in fully certified safe states.
3. **Unresolved general boundary:** PPO has not yet learned a stable LEFT-versus-KEEP classifier that satisfies all safety and completion gates.

The bottleneck is currently not road geometry or basic maneuver execution. It is the conversion of correct option-level return information into a stable actor update across both preference classes.

## 9. Recommended Next Steps

1. Freeze the Stage 4.8R update-2 rollout buffer.
2. Decompose every sample's contribution to the LEFT-minus-KEEP gradient.
3. Separate lane-head and lane-encoder contributions.
4. Bucket contributions by required class, sampled action, action probability, and PPO clipping state.
5. Identify why correct action-conditioned GAE produces a negative aggregate margin gradient.
6. Make only the smallest optimizer or credit-aggregation correction supported by that evidence.
7. Restart from the accepted Stage 4.7 partial checkpoint, not either rejected Stage 4.8R checkpoint.
8. Re-run the decisive static bank.
9. Require LEFT and KEEP accuracy of at least 90%, overall preference accuracy of at least 90%, unsafe entry at most 5%, and collision gates.
10. Re-run FLEXIBLE retention and broader sparse/dense/stress diagnostics.
11. Only after the static boundary passes, begin dynamic gap-preparation PPO with the merge residual.
12. Defer general rightward, multi-lane, destination-planning, and pocket PPO until the single adjacent merge is solved.

## 10. Definitions

### Lane segment

A directed, locally continuous piece of road with a stable ID, geometry, predecessors, successors, and adjacency relationships.

### Station-dependent adjacency

The neighboring lane can change with longitudinal position. A lane may have a left neighbor upstream but no neighbor after it terminates.

### Lane intent

The policy's high-level categorical decision to KEEP, move LEFT, or move RIGHT.

### Topology mask

A mask that removes physically nonexistent actions. It can block RIGHT when no right-hand lane exists. It does not decide whether a valid LEFT action is safe.

### Persistent option

A high-level action that remains active for multiple physics steps. It prevents repeated resampling during one maneuver.

### Semi-Markov decision process

A decision process where actions can last different numbers of low-level steps. Option return uses accumulated reward and a duration-dependent `gamma^k` bootstrap.

### Merge residual

A small experimental acceleration adjustment associated with merge preparation. It is currently zero and frozen so lane-intent learning can be diagnosed independently.

### Merge oracle

A deterministic engineering model that classifies gap feasibility from geometry and relative motion. It is a diagnostic and certification tool, not the learned policy.

### Scenario bank

A fixed, preregistered collection of seeds, scenarios, or copied decision states used for training or evaluation.

### Copied-state counterfactual

Two branches starting from exactly the same simulator, policy, and RNG state, differing only in the first tested option.

### Preference accuracy

The fraction of decisive states where the policy's deterministic option matches the physically certified immediate preference.

### FLEXIBLE state

A state where LEFT now and KEEP for one option interval both preserve a materially equivalent safe outcome.

### Monte Carlo return

The discounted sum of observed future rewards from a state or option branch.

### Critic

The network that estimates expected future return and supplies a baseline for the actor update.

### GAE

Generalized Advantage Estimation. It estimates whether the sampled action performed better or worse than the critic expected.

### Credit assignment

Determining which earlier decision should receive credit or blame for a delayed completion, collision, unsafe entry, or lane-end failure.

### Policy collapse

The policy loses conditional behavior and selects one action almost everywhere, such as always-KEEP or always-LEFT.

### Unsafe entry

A merge commitment made when target-lane geometry or relative motion violates the certified safety conditions.

### Opportunity acceptance

The fraction of valid safe merge opportunities that the policy actually takes.

## 11. Tough Meeting Questions and Answers

### Q1. Can the current production policy change lanes?

**No.** Production V5 uses `legacy_path_v1`. Segment topology and learned lane intent remain experimental.

### Q2. Have we learned anything, or is everything scripted?

We learned a real but narrow behavior. Stage 4.7 PPO learned deterministic LEFT on a disjoint certified-safe bank with 100% completion and zero safety events. Topology and trajectory execution are deterministic infrastructure. The general safe/unsafe choice is not solved.

### Q3. Is runtime control pure RL?

The accepted experimental high-level lane decision is a PPO policy output with no oracle action replacement or runtime shield. The lateral trajectory is a deterministic low-level controller. Therefore the behavioral decision is learned, while physical path execution is model-based.

### Q4. Why not make the policy learn the entire lateral trajectory?

That would combine two problems: deciding whether a merge is appropriate and discovering physically smooth path geometry. A hierarchical design reduces exploration risk, improves sample efficiency, and makes failures attributable. A future V6 lateral controller can be learned after the decision layer is reliable.

### Q5. Why is route validity not learned?

Road connectivity is an environment fact, like a wall or lane boundary. The topology mask removes nonexistent actions. The policy still learns which valid route action is behaviorally appropriate.

### Q6. Why was RIGHT never selected?

The current auxiliary lane lies to the right of its continuing target lane, so LEFT is the only valid escape. RIGHT has no adjacent drivable segment and is topologically masked. Rightward scenarios have not yet been trained.

### Q7. Why not simply train longer?

The failed update-3 buffer showed a negative actor gradient despite correctly ordered LEFT-required advantages. More steps with the same update rule could strengthen the wrong direction. The optimizer signal must be decomposed first.

### Q8. Why not increase the LEFT reward?

The exact decisive-bank Monte Carlo and GAE comparisons already prefer LEFT when LEFT is physically required. Increasing reward without locating the gradient contradiction could create more unsafe always-LEFT behavior.

### Q9. Why did the early balanced prewarm not solve it?

Balanced offline labels do not reproduce the state distribution created by the policy's own actions. The prewarmed classifier did not remain balanced during closed-loop rollouts and did not solve delayed consequences.

### Q10. Did we use DAgger or imitation learning?

No DAgger was used in the accepted lane stages. Early experiments used bounded offline supervised prewarm as diagnostic scaffolding. Stages 4.3 through 4.8R used PPO for learned behavior, with offline counterfactuals restricted to certification and evaluation.

### Q11. What exactly did Stage 4.7 prove?

It proved that the architecture, observations, PPO implementation, and trajectory executor can learn and perform a safe merge when every decision state genuinely favors LEFT. It did not prove that the policy can distinguish safe from unsafe merges.

### Q12. Why was Stage 4.7 rejected outside its narrow scope?

It generalized LEFT too broadly. On the static mixed bank it had 34.78% unsafe entries and 11.72% collision events, effectively an always-LEFT policy.

### Q13. What did Stage 4.8R change?

It changed the definition of the training bank, not rewards or runtime semantics. It removed states where both LEFT and one interval of KEEP were valid and retained only true immediate LEFT-required and KEEP-required states.

### Q14. What is the strongest Stage 4.8R result?

Update 1 reached 91.96% physical preference accuracy, 100% LEFT-required completion, zero LEFT-required collisions, and 91.21% KEEP in unsafe states. It still failed because unsafe entry was 8.79%, above the 5% gate.

### Q15. Why call this an optimization/credit-aggregation issue?

At the blocked third update, LEFT-required samples gave LEFT substantially higher raw GAE than KEEP, but the predicted LEFT-logit gradient was negative. The return signal was correct while the aggregated actor update direction was wrong.

### Q16. Could the critic be wrong?

It remains a candidate contributor, but exact paired Monte Carlo and GAE ordering passed in the decisive bank. The next audit will separate critic, normalization, action-probability, lane-head, and shared-encoder contributions rather than assume one source.

### Q17. Why retain FLEXIBLE states?

They test whether the policy preserves valid behavior without pretending there is one correct immediate action. They are important for detecting needless conservatism or over-aggressive merging after the decisive boundary is learned.

### Q18. Why is the merge residual frozen?

Allowing longitudinal preparation to change simultaneously would make it unclear whether failures came from lane intent or speed control. Static intent must pass first; then the residual can learn dynamic gap preparation.

### Q19. What would count as a successful next checkpoint?

At minimum: LEFT-required and KEEP-required accuracy at least 90%, overall preference accuracy at least 90%, required completion at least 90%, unsafe entry at most 5%, collision events at most 2%, collision-involved vehicles at most 4%, no topology defects, comfort preserved, and no one-action collapse.

### Q20. What is the immediate next technical experiment?

Run a paired per-sample actor-gradient decomposition on the frozen Stage 4.8R update-2 buffer. Determine exactly where the correct option advantages become a negative LEFT-minus-KEEP gradient before applying another optimizer update.

## 12. Closing Statement

The merge project is no longer blocked by lane geometry, trajectory continuity, collision detection, or missing observations. It has also demonstrated genuine PPO acquisition of a safe merge action. The remaining research problem is narrower: make the lane-intent actor reliably convert correct option-level consequences into a stable conditional LEFT-versus-KEEP policy without collapsing toward either extreme.

## 13. Authoritative References

- `intersection-rl_stage4_4_credit_audit_persistent_intent/results/stage4_4_credit_audit_persistent_intent_2026_07_27/STAGE4_4_REPORT.md`
- `intersection-rl_stage4_5_pure_ppo_safe_acquisition/results/stage4_5_pure_ppo_safe_acquisition_2026_07_27/STAGE4_5_REPORT.md`
- `intersection-rl_stage4_6_certified_safe_decision_acquisition/results/stage4_6_certified_safe_decision_acquisition_2026_07_28_authoritative/STAGE4_6_REPORT.md`
- `intersection-rl_stage4_7_high_exposure_safe_acquisition/results/stage4_7_high_exposure_safe_acquisition_2026_07_28_authoritative/STAGE4_7_REPORT.md`
- `intersection-rl_stage4_8_certified_static_merge_boundary/results/stage4_8_certified_static_merge_boundary_2026_07_28_authoritative/STAGE4_8_REPORT.md`
- `intersection-rl_stage4_8r_option_credit_alignment/results/stage4_8r_option_credit_alignment_2026_07_28_authoritative/STAGE4_8R_REPORT.md`
