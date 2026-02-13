"""Tests for chat agent — intent detection and graph routing."""

from istari.agents.chat import Intent, _detect_intent, chat_graph


class TestIntentDetection:
    # --- TODO capture ---

    def test_todo_prefix(self):
        intent, content = _detect_intent("TODO: review the PR")
        assert intent == Intent.TODO_CAPTURE
        assert content == "review the PR"

    def test_todo_lowercase(self):
        intent, content = _detect_intent("todo buy milk")
        assert intent == Intent.TODO_CAPTURE
        assert content == "buy milk"

    def test_remind_me_to(self):
        intent, content = _detect_intent("remind me to call the dentist")
        assert intent == Intent.TODO_CAPTURE
        assert content == "call the dentist"

    def test_add_todo(self):
        intent, content = _detect_intent("add todo: send the report")
        assert intent == Intent.TODO_CAPTURE
        assert content == "send the report"

    def test_create_task(self):
        intent, content = _detect_intent("create a task: fix the login bug")
        assert intent == Intent.TODO_CAPTURE
        assert content == "fix the login bug"

    def test_need_to(self):
        intent, content = _detect_intent("I need to finish the slides")
        assert intent == Intent.TODO_CAPTURE
        assert content == "finish the slides"

    def test_dont_forget(self):
        intent, content = _detect_intent("don't forget to water the plants")
        assert intent == Intent.TODO_CAPTURE
        assert content == "water the plants"

    # --- Memory write ---

    def test_remember_that(self):
        intent, content = _detect_intent("remember that I prefer mornings")
        assert intent == Intent.MEMORY_WRITE
        assert content == "I prefer mornings"

    def test_note_that(self):
        intent, content = _detect_intent("note that the deadline is Friday")
        assert intent == Intent.MEMORY_WRITE
        assert content == "the deadline is Friday"

    def test_i_prefer(self):
        intent, content = _detect_intent("I prefer dark mode")
        assert intent == Intent.MEMORY_WRITE
        assert content == "dark mode"

    def test_i_like(self):
        intent, content = _detect_intent("I like working in the morning")
        assert intent == Intent.MEMORY_WRITE
        assert content == "working in the morning"

    def test_fyi(self):
        intent, content = _detect_intent("FYI, the server IP changed to 10.0.0.1")
        assert intent == Intent.MEMORY_WRITE
        assert "server IP" in content

    # --- Prioritize ---

    def test_what_should_i_work_on(self):
        intent, _ = _detect_intent("What should I work on?")
        assert intent == Intent.PRIORITIZE

    def test_what_should_i_do(self):
        intent, _ = _detect_intent("what should I do?")
        assert intent == Intent.PRIORITIZE

    def test_show_priorities(self):
        intent, _ = _detect_intent("show my priorities")
        assert intent == Intent.PRIORITIZE

    def test_prioritize(self):
        intent, _ = _detect_intent("prioritize my tasks")
        assert intent == Intent.PRIORITIZE

    # --- General chat ---

    def test_general_greeting(self):
        intent, _ = _detect_intent("Hello!")
        assert intent == Intent.CHAT

    def test_general_question(self):
        intent, _ = _detect_intent("What is the capital of France?")
        assert intent == Intent.CHAT

    def test_general_conversation(self):
        intent, _ = _detect_intent("Tell me about quantum computing")
        assert intent == Intent.CHAT


class TestChatGraph:
    async def test_todo_capture_flow(self):
        result = await chat_graph.ainvoke({"user_message": "TODO: review the PR"})
        assert result["intent"] == Intent.TODO_CAPTURE.value
        assert result["extracted_content"] == "review the PR"
        assert "review the PR" in result["response"]

    async def test_memory_write_flow(self):
        result = await chat_graph.ainvoke(
            {"user_message": "remember that I prefer mornings"}
        )
        assert result["intent"] == Intent.MEMORY_WRITE.value
        assert "remember" in result["response"].lower() or "noted" in result["response"].lower()

    async def test_prioritize_flow(self):
        result = await chat_graph.ainvoke(
            {"user_message": "What should I work on?"}
        )
        assert result["intent"] == Intent.PRIORITIZE.value
        assert result["response"] == "__PRIORITIZE__"

    async def test_chat_flow(self):
        result = await chat_graph.ainvoke({"user_message": "Hello!"})
        assert result["intent"] == Intent.CHAT.value
        assert result["response"] == "__LLM_CALL__"

    async def test_sensitive_content_flagged(self):
        result = await chat_graph.ainvoke(
            {"user_message": "email john@example.com about the meeting"}
        )
        assert result["is_sensitive"] is True


class TestIntentEdgeCases:
    def test_empty_string(self):
        intent, _ = _detect_intent("")
        assert intent == Intent.CHAT

    def test_only_whitespace(self):
        intent, _ = _detect_intent("   ")
        assert intent == Intent.CHAT

    def test_todo_colon_no_space(self):
        intent, _content = _detect_intent("TODO:fix the bug")
        assert intent == Intent.TODO_CAPTURE

    def test_mixed_case_todo(self):
        intent, _ = _detect_intent("Todo: clean up the code")
        assert intent == Intent.TODO_CAPTURE

    def test_remember_to_is_todo_not_memory(self):
        # "remind me to" → TODO, not memory
        intent, _ = _detect_intent("remind me to buy groceries")
        assert intent == Intent.TODO_CAPTURE

    def test_what_should_i_focus_on(self):
        intent, _ = _detect_intent("what should I focus on?")
        assert intent == Intent.PRIORITIZE

    def test_i_hate_early_meetings(self):
        intent, content = _detect_intent("I hate early morning meetings")
        assert intent == Intent.MEMORY_WRITE
        assert "early morning meetings" in content

    def test_get_top_tasks(self):
        intent, _ = _detect_intent("get my top tasks")
        assert intent == Intent.PRIORITIZE

    def test_list_priorities(self):
        intent, _ = _detect_intent("list my priorities")
        assert intent == Intent.PRIORITIZE

    def test_keep_in_mind(self):
        intent, content = _detect_intent("keep in mind that I'm off on Fridays")
        assert intent == Intent.MEMORY_WRITE
        assert "off on Fridays" in content
