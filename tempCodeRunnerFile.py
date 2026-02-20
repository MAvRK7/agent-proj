from orchestrator import orchestrator

if __name__ == "__main__":
    print("Welcome to the INR to AUD assistant!")
    print("Type 'exit' to quit.")
    
    while True:
        user_input = input("\nEnter your query: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        
        response = orchestrator(user_input)
        print("\nAssistant:", response)