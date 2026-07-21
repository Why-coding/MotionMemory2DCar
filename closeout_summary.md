**Closeout Summary**

You can present the last two weeks in four parts: environment correctness, policy architecture, yielding development, and the transition toward realistic vehicle dynamics.

**1. What I Completed**

During the first week, I made the intersection environment physically and legally consistent:

- Corrected stop-line geometry from vehicle-center to front-bumper measurements.
- Changed route completion to rear-bumper clearance.
- Added legal intersection-clearance and one-shot dilemma-zone handling.
- Added yellow phases and 3.5-second all-red clearance.
- Restored protected-left signal phases with separate left-turn lamps.
- Unified simulation and evaluation scenario construction.
- Added random legal signal initialization and feasible random vehicle spawning.
- Added zebra crossings and pedestrian agents.
- Added package provenance checks to prevent stale code from silently being evaluated.
- Expanded automated regression coverage to more than 250 tests.

This produced the validated production checkpoint:

`protected_redgreen_front_bumper_polish_v1b_200k_selected.npz`

Its training run completed 202,752 rollout steps over 66 PPO updates. Update 35 was selected. Under the current straight-through protocol, it completes all nine sparse, dense, and stress cells through four lanes and 48 cars with zero recorded safety events. It also passes the tested yellow stop/clear matrix.

**2. Yielding Features**

During the second week, I implemented three new yielding tasks:

- Mandatory-stop right-on-red followed by gap acceptance.
- Pedestrian yielding at crosswalks.
- Unprotected-left yielding to opposing traffic.

I added:

- Right-turn route generation restricted to the rightmost source lane.
- Route, signal, pedestrian, front-gap, relative-speed, conflict and opportunity observations.
- Mandatory right-on-red stop-duration tracking.
- Dynamic TTC and predicted conflict occupancy.
- Opportunity metrics, so a policy cannot appear safe simply by waiting forever.
- Priority-vehicle defensive-braking metrics.
- Focused, combined, sparse, dense and stress evaluation suites.
- Zero-initialized graph-attention adapters that preserve old checkpoint behavior before training.

The strongest validated partial checkpoint is:

`yield_ppo_v1_ror_ped_partial.npz`

It contains 53,248 PPO steps and cleanly learns right-on-red and pedestrian yielding in focused evaluations. Unprotected left is intentionally not learned by this checkpoint.

The strongest current combined-yield-and-creep experiment is:

`polish_v26_creep_yield_combined_ppo_probe_100k_v1_best.npz`

It was selected after 45 PPO updates and 92,160 environment steps. It demonstrates all three yielding behaviors, but it is experimental. Combined sparse, dense and stress tests still have collision-event rates of approximately 5.28%, 5.83% and 7.22%, so it has not passed the production threshold.

**3. Main Challenges And Solutions**

| Challenge | Diagnosis | Solution |
|---|---|---|
| Cars visually crossed the line while “legal” | Center and bumper geometry were mixed | One front-bumper convention for spawning, observations, stopping and violations |
| Vehicles stopped inside the intersection after signal changes | Legal clearers were being shown a closed movement | Clearance eligibility remains active until the rear bumper exits |
| Unavoidable red violations at phase changes | Future phase timing was unobservable | Yellow warning plus one-shot physical dilemma-zone eligibility |
| Policy learned to stop but not move | Safe all-stop behavior was a local optimum | Opportunity-taking rewards, gap-opening curricula and acceptance metrics |
| Lead vehicles stopped far upstream | Brake and creep required conflicting actions | Separate brake, creep and go policy components with a creep speed servo |
| Deep queues released too slowly | Sequential follower response and weak deep-queue coverage | Queue-position diagnostics, lead-speed observations and following-response adapters |
| Yielding worked separately but failed when combined | Shared features and multi-agent interactions interfered | Scoped graph adapters, task-retention mixes and combined qualification |
| PPO erased previously learned behavior | Shared-trunk catastrophic forgetting | Reference KL, frozen/zero-initialized adapters, replay and hard promotion floors |
| Gate learning was overwhelmed | Value gradients dominated auxiliary gradients | Separate diagnostics, Huber value loss, gradient scaling and per-loss gradient logging |
| Simulation disagreed with evaluation | Different builders and settings were used | Shared scenario builder and startup provenance banner |

**4. Why Prewarm Was Necessary**

Prewarm initializes a new policy head or routing component using representative simulator states before PPO begins. It was useful because safety-critical states are rare and random exploration may never discover successful behavior.

For example, right-on-red requires this sequence:

1. Approach the red signal.
2. Stop at the line.
3. Wait for the mandatory duration.
4. Observe a safe finite gap.
5. Enter without causing another vehicle to brake sharply.
6. Complete the turn.

A randomly initialized component is unlikely to execute the entire sequence successfully. Without successful examples, PPO receives mostly collision penalties or learns that never moving is safest.

Prewarm therefore provided an initial representation of brake, creep, go and yield states. PPO was still required to learn from rewards where the actual gap-acceptance boundary should be.

An important lesson was that prewarm had initially been overused. Some early “yield checkpoints” had zero PPO steps and were therefore supervised diagnostics, not learned RL policies. The project corrected this by:

- Recording PPO-step provenance in checkpoints.
- Rejecting prewarm-only artifacts as learned policies.
- Requiring positive PPO training for new behavior.
- Keeping prewarm as initialization, not final training.

**5. Why Auxiliary Loss Was Necessary**

The PPO reward answers whether an episode outcome was good. It does not efficiently tell every internal component what representation it should learn.

Training-only auxiliary losses help with:

- Routing observations into brake, creep, go or yield components.
- Predicting conflict occupancy and required braking.
- Teaching the creep component to regulate around a low target speed.
- Preserving previously learned green-driving and stopping behavior.
- Making rare safety states contribute meaningful gradients.

Conceptually, training uses:

`PPO policy loss + value loss + entropy + scoped auxiliary losses + retention KL`

These losses accelerate and stabilize learning. They do not replace PPO outcome learning.

The accurate claim is:

> The controller is policy-only at runtime, but training is PPO with optional auxiliary supervision and retention regularization.

At runtime, acceleration and steering come directly from the neural network. The safety shield is disabled. Signal laws, route geometry and clearance eligibility are environment semantics; they do not select or override the policy action.

**6. Jerk Limit And Kinodynamics**

There is one important correction for the meeting: the repository currently still uses a basic kinematic update. The policy directly requests acceleration every 0.2 seconds, and acceleration can change immediately between steps. The code currently marks jerk-limited kinodynamics as the next development stage; it is not yet fully implemented.

State it this way:

> I have started the transition from the basic kinematic model to a jerk-limited kinodynamic model.

That transition will introduce:

- Acceleration as a persistent vehicle state.
- A bound on acceleration change: `|a(t+1) - a(t)| / dt <= jerk_limit`.
- Physically consistent speed and position integration.
- Steering-angle and steering-rate constraints.
- Curvature and lateral-acceleration limits during turns.
- Smoothness and passenger-comfort metrics.
- New training and regression tests under the changed dynamics.

This is necessary because the current model allows instantaneous braking and acceleration changes. A jerk-limited model prevents the policy from exploiting unrealistic actuator behavior, produces smoother trajectories and improves transferability to a real vehicle or higher-fidelity simulator.

**Closing Statement**

> In the last two weeks, I moved the project from a visually plausible but semantically inconsistent intersection simulation to a tested, bumper-correct, policy-controlled system with red, green, yellow, protected-left, pedestrians and experimental learned yielding. The straight/yellow policy is validated; right-on-red and pedestrian yielding are strong in focused tests; combined yielding remains experimental because its collision rate is above the promotion threshold. The next technical phase is jerk-limited kinodynamics followed by combined-yield retraining and qualification under those more realistic dynamics.

The detailed supporting records are in [REPORT.md](/home/dd/Desktop/AV%20Internship/PP/intersection-rl_generalized/REPORT.md), [RUN_SUMMARY.md](/home/dd/Desktop/AV%20Internship/PP/intersection-rl_generalized/RUN_SUMMARY.md), and [CHECKPOINT_REGISTRY.md](/home/dd/Desktop/AV%20Internship/PP/intersection-rl_generalized/CHECKPOINT_REGISTRY.md).
