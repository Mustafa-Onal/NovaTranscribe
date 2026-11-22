from ollama_client import ask_nova


def main():
    prompt = input("Sen: ").strip()
    if not prompt:
        print("Lütfen bir mesaj yazın.")
        return

    response = ask_nova(prompt)
    print("Nova:", response)


if __name__ == "__main__":
    main()