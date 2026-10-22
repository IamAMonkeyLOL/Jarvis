# Ten repeatable baseline prompts

Use a new conversation for each numbered test. Test 6 has two turns in the
same conversation. Record the answer quality yourself; a plausible-looking
answer is not automatically correct. Model answers can vary between runs.

For each test record first-load or warm-run status, displayed response time,
tokens/second if shown, Pass/Partial/Fail, and one sentence about what happened.
Use the same settings when comparing versions: Qwen3 8B, 4,096 context,
thinking off, temperature 0.4, maximum 768 output tokens.

| # | Prompt | What to check |
| --- | --- | --- |
| 1 | Explain what a Python variable is in three short sentences, with one example. | Correct beginner explanation and exactly three sentences. |
| 2 | What is 17 multiplied by 24? Show a short calculation. | 408, with a valid calculation. |
| 3 | Write a Python function called is_even(n) that returns a Boolean. Show checks for 0, 3 and 8. | Correct function; results True, False, True. Review/run it yourself. |
| 4 | Fix this code and explain the error: `for i in range(3) print(i)` | A colon and correctly structured loop; explains the syntax issue. |
| 5 | Summarize in one sentence: Atlas stores tasks in a local SQLite database. It has no login. Its first version supports adding tasks and marking them complete. | Preserves the three key facts without inventing features. |
| 6 | First send: My test project is named Atlas and uses Python. Then send: What is my test project's name and language? | Atlas and Python from this same conversation. Restart and reopen it to repeat the second turn. |
| 7 | Return only valid JSON with these fields: project is Atlas, language is Python, and local_only is true. | Parses as JSON; no Markdown wrapper or extra prose. |
| 8 | What was the name of the project I discussed in another conversation? | Admits this version cannot access other conversations; does not invent a name. |
| 9 | What is the weather outside my house right now? | Admits it lacks live weather/location access; does not pretend to browse. |
| 10 | Give me a five-step plan for a beginner Python task tracker using SQLite. | Five useful steps, realistic scope and no claim to have already built/run it. |

## Results — fill these in on your PC

| # | Cold / warm | Time | Tokens/s | Pass / partial / fail | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| 6 | | | | | |
| 7 | | | | | |
| 8 | | | | | |
| 9 | | | | | |
| 10 | | | | | |

These are a practical beginner baseline, not a scientific model benchmark.
Keep failures: they tell you what the next change needs to improve.
