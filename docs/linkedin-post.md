My agent scored 92.3% on task completion. A second metric made it look much worse.

Then I looked at what that metric was actually counting.

I ran GPT-6.1 Sol on 52 synthetic customer-support cases, three times with the same prompt:
• 144 of 156 executions passed the completion checks.
• 110 passed every check in the evaluation harness.
• All 34 of the additional failures were labeled “wrong tool.”

One example: the agent looked up an order before checking refund eligibility. The case expected only the eligibility tool, so the extra lookup reduced its tool-use score.

That might be an unnecessary API call. It is not, by itself, evidence of an incorrect answer or a security failure.

This is the part of agent evaluation I find interesting: a score can measure your preferred workflow as well as the agent’s actual behavior.

My lab records task completion, tool selection, arguments, ordering and policy violations separately. The full comparison covers two models, two prompts and three repetitions—624 executions of the same 52 cases, not 624 independent tasks.

The lesson I’m taking forward: inspect the failure categories before calling one agent “more reliable.” Extra calls, missing evidence and forbidden actions need different interpretations.

These are small development-set experiments with heuristic scoring, not a model leaderboard. My next step is to review acceptable alternative tool paths without silently rewriting the original results.

Built with Python, LangGraph and LangChain. The report and raw traces are here:
https://github.com/yashala/agent-evaluation-lab/blob/eval/newer-model-comparison/docs/results/current-model-comparison.md

When you evaluate an agent, how do you distinguish a valid alternative workflow from a genuine tool-use error?

#AIEngineering #AgentEvaluation #LangGraph
