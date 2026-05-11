import anthropic
import streamlit as st

st.set_page_config(page_title="Travel Agent", page_icon="✈️")
st.title("✈️ Travel Agent")
st.caption("Ask me anything about destinations, attractions, or budgets.")

client = anthropic.Anthropic()

tools = [
    {"name": "get_weather",
     "description": "Get weather conditions for a travel destination. READ ONLY.",
     "input_schema": {"type": "object",
       "properties": {"city": {"type": "string"}, "month": {"type": "string"}},
       "required": ["city"]}},
    {"name": "search_attractions",
     "description": "Find top tourist attractions in a city. READ ONLY.",
     "input_schema": {"type": "object",
       "properties": {"city": {"type": "string"}, "category": {"type": "string"}},
       "required": ["city"]}},
    {"name": "estimate_budget",
     "description": "Estimate daily travel budget in INR for a destination.",
     "input_schema": {"type": "object",
       "properties": {"city": {"type": "string"},
         "style": {"type": "string", "enum": ["budget", "mid-range", "luxury"]}},
       "required": ["city", "style"]}},
]

def execute_tool(name, inputs):
    if name == "get_weather":
        return f"{inputs['city']}: 22-28 degrees C, sunny. Best travel months: Oct-Mar."
    elif name == "search_attractions":
        return f"Top in {inputs['city']}: Old Town, Night Market, Temple District, Viewpoint, Botanical Garden."
    elif name == "estimate_budget":
        budgets = {"budget": 2500, "mid-range": 6000, "luxury": 15000}
        return f"Daily in {inputs['city']} ({inputs['style']}): Rs {budgets[inputs['style']]:,} all-in."
    return "Tool not found."

def run_travel_agent(query, status_container):
    messages = [{"role": "user", "content": query}]
    while True:
        r = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1000,
            system="You are a travel assistant. Use tools to give accurate, specific answers.",
            tools=tools, messages=messages)
        if r.stop_reason == "end_turn":
            for block in r.content:
                if hasattr(block, "text"):
                    return block.text
            return "Done."
        tool_results = []
        for block in r.content:
            if block.type == "tool_use":
                status_container.info(f"🔧 Calling `{block.name}` with `{block.input}`")
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })
        messages += [
            {"role": "assistant", "content": r.content},
            {"role": "user", "content": tool_results}
        ]

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if query := st.chat_input("Where do you want to travel?"):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        status = st.empty()
        with st.spinner("Thinking..."):
            response = run_travel_agent(query, status)
        status.empty()
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
