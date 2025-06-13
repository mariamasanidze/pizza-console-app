import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load Gemini API key
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Menu (all lowercased for normalization)
menu = {
    "pizzas": {"margherita": 8, "pepperoni": 10, "veggie": 9, "bbq chicken": 11},
    "sizes": ["small", "medium", "large"],
    "toppings": {"olives": 1, "mushrooms": 1, "extra cheese": 1.5, "onions": 1, "bacon": 2},
    "drinks": {"coke": 2, "pepsi": 2, "water": 1},
    "sides": {"garlic bread": 3, "fries": 2.5}
}

# State machine
states = ["pizza_type", "pizza_size", "toppings", "drinks", "sides", "confirm"]
current_state = 0
order = {}

# Function declarations for Gemini Function Calling
functions = {
    "pizza_type": {
        "name": "extract_pizza_type",
        "description": "Extract pizza type",
        "parameters": {
            "type": "object",
            "properties": {"pizza_type": {"type": "string"}},
            "required": ["pizza_type"]
        }
    },
    "pizza_size": {
        "name": "extract_pizza_size",
        "description": "Extract pizza size",
        "parameters": {
            "type": "object",
            "properties": {"size": {"type": "string"}},
            "required": ["size"]
        }
    },
    "confirm": {
        "name": "extract_confirm",
        "description": "Extract confirmation",
        "parameters": {
            "type": "object",
            "properties": {"confirm": {"type": "boolean"}},
            "required": ["confirm"]
        }
    }
}

# Prompts
def get_prompt():
    prompts = {
        "pizza_type": f"Which pizza would you like? {', '.join(menu['pizzas'].keys())}",
        "pizza_size": f"Which size? {', '.join(menu['sizes'])}",
        "toppings": f"Any toppings? {', '.join(menu['toppings'].keys())}",
        "drinks": f"Any drinks? {', '.join(menu['drinks'].keys())}",
        "sides": f"Any sides? {', '.join(menu['sides'].keys())}",
        "confirm": "Do you confirm your order? (yes/no)"
    }
    return prompts[states[current_state]]

# Fuzzy extractor for toppings, drinks, sides
def extract_keywords(user_input, category):
    found = []
    for item in menu[category]:
        if item in user_input.lower():
            found.append(item)
    return found

# Start ordering
print("\n🍕 Welcome to AI Pizza Shop!\n")
print("AI:", get_prompt())

while True:
    user_input = input("You: ")
    slot = states[current_state]

    # Hybrid system: use function calling only for type, size, confirm
    if slot in ["pizza_type", "pizza_size", "confirm"]:
        model = genai.GenerativeModel("gemini-1.5-flash", tools=[{"function_declarations": [functions[slot]]}])
        response = model.generate_content(user_input)
        part = response.candidates[0].content.parts[0]

        if not hasattr(part, "function_call") or part.function_call.args is None:
            print("AI: Sorry, I didn’t understand. Try again.")
            print("AI:", get_prompt())
            continue

        args = dict(part.function_call.args)

        # Handle each structured slot
        if slot == "pizza_type":
            value = args["pizza_type"].lower()
            if value in menu["pizzas"]:
                order["Pizza"] = value
            else:
                print("AI: Invalid pizza type.")
                print("AI:", get_prompt())
                continue

        elif slot == "pizza_size":
            value = args["size"].lower()
            if value in menu["sizes"]:
                order["Size"] = value
            else:
                print("AI: Invalid size.")
                print("AI:", get_prompt())
                continue

        elif slot == "confirm":
            if args["confirm"]:
                # Print summary
                print("\n✅ Order confirmed! Summary:")
                total = 0
                pizza = order["Pizza"]
                size = order["Size"]
                subtotal = menu["pizzas"][pizza] * {"small": 1, "medium": 1.2, "large": 1.5}[size]
                total += subtotal
                print(f"- {size.title()} {pizza.title()}: ${subtotal:.2f}")

                for t in order.get("Toppings", []):
                    total += menu["toppings"][t]
                    print(f"- Topping: {t.title()} (${menu['toppings'][t]:.2f})")

                for d in order.get("Drinks", []):
                    total += menu["drinks"][d]
                    print(f"- Drink: {d.title()} (${menu['drinks'][d]:.2f})")

                for s in order.get("Sides", []):
                    total += menu["sides"][s]
                    print(f"- Side: {s.title()} (${menu['sides'][s]:.2f})")

                print(f"\nTotal: ${total:.2f}\nThank you for ordering 🍕")
                break
            else:
                print("AI: Order cancelled. Restarting...")
                order.clear()
                current_state = 0
                print("AI:", get_prompt())
                continue

    else:
        # Use pure Gemini chat for free-form slots
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Extract relevant {slot} from: {user_input}")
        extracted = extract_keywords(user_input, slot)

        if slot == "toppings":
            order["Toppings"] = extracted
        elif slot == "drinks":
            order["Drinks"] = extracted
        elif slot == "sides":
            order["Sides"] = extracted

    # Move to next state
    current_state += 1
    if current_state < len(states):
        print("AI:", get_prompt())
