"""OSLLM chat: ask the Process Scheduling LLM anything.   Start with:  bash run.sh"""
from osllm_client import ask, check_ready

HISTORY_TURNS = 10


def main():
    check_ready()
    print("=" * 60)
    print(" OSLLM - Process Scheduling LLM")
    print(" Ask any process scheduling question or numerical problem.")
    print(" Commands:  clear = new conversation   exit = quit")
    print("=" * 60 + "\n")
    history = []
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break
        if question.lower() == "clear":
            history = []
            print("Conversation cleared.\n")
            continue
        print("\nOSLLM: ", end="", flush=True)
        try:
            answer = ask(history[-HISTORY_TURNS:] + [{"role": "user", "content": question}])
        except KeyboardInterrupt:
            print("\n(stopped)\n")
            continue
        except Exception as e:
            print(f"\nError: {e}\n")
            continue
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
        print()


if __name__ == "__main__":
    main()
