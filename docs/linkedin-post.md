92.3% task completion looked reassuring. The tool traces told a more complicated story.

I evaluated a customer-support agent on 52 synthetic cases, with three runs per configuration.

Using the same v1 prompt:
• GPT-6.1 Sol: 144/156 executions passed the completion checks; 110/156 were clean.
• GPT-6 Luna: 129/156 passed completion; 114/156 were clean.

That is 92.3% completion versus 70.5% clean execution for Sol, and 82.7% versus 73.1% for Luna.

Those 156 executions per configuration repeat the same 52 cases. They are not 156 independent tasks.

The distinction comes from what the harness checks. Completion looks for an acceptable outcome and expected facts. A clean trace also requires acceptable tool selection, arguments, ordering, and no recorded policy or grounding failure. Blocked attempts still count.

I’m interested in that gap because an acceptable final response can conceal a problematic execution path.

But the evaluator deserves scrutiny too. This scorer uses substring fact checks and heuristic outcome detection. “Clean” means it passed those checks; it does not establish production safety. A few percentage points on this small development set are not evidence of a universal model ranking.

The full experiment covers two models, two prompts and three repetitions: 624 executions. Both models used low reasoning effort and the same output cap. The abbreviated v2 prompt also removes instructions, so it is not an isolated efficiency experiment.

Built with Python, LangGraph and LangChain, with saved traces and a comparison dashboard. The next useful step is held-out cases and manual review of scorer disagreements.

Would your agent still pass if you graded its tool trace separately from its final answer?

https://github.com/yashala/agent-evaluation-lab/blob/eval/newer-model-comparison/docs/results/current-model-comparison.md

#AIEngineering #AgentEvaluation #LangGraph
