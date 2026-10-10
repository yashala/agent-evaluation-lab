# Limitations

- **Small, synthetic, self-authored.** 52 cases written with the agent, by the same process.
  Expectations were corrected after reading model traces. Results are development-set numbers.
- **One run per configuration.** No repeated runs, so no variance estimate; one case = 1.9 points.
- **One provider.** OpenAI `gpt-4.1-mini` and `gpt-4.1-nano`; conclusions may not transfer.
- **The policy blocks everything here.** Safety numbers describe what the model attempted under
  this policy, not how a system without it would behave in production.
- **String-match facts.** Paraphrased answers can be scored as incomplete.
- **Prompt v2 is one variant.** It shows that a prompt change can trade cost for behaviour; it
  does not characterise prompts in general.
- **Single-turn conversations.** Multi-turn clarification flows are not evaluated.
- **Latency** was measured on an 8 GB laptop with network calls to OpenAI; it is reported but
  not analysed.

What a production version would need: multi-turn and adversarial cases from real support logs
(with consent), repeated runs with confidence intervals, human review of expectations, a
policy layer tested independently, and online monitoring of attempted violations.
