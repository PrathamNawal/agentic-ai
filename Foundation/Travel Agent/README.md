# 🌍 AI-Powered Travel Agent

An intelligent travel planning assistant that generates personalized, day-by-day itineraries based on your preferences and exports them directly to your digital calendar.

## ✨ Features

- **Personalized Planning**: Leveraging the power of GPT-4o (via OpenRouter) to create itineraries tailored to your unique interests.
- **Flexible Customization**: Define your destination, trip duration, budget tier, and traveling companions.
- **Rich Visualization**: Beautifully formatted Markdown itineraries delivered right in your Jupyter environment.
- **Calendar Integration**: One-click export to `.ics` format, compatible with Google Calendar, Apple Calendar, and Outlook.
- **Smart Logic**: Considers travel time, budget constraints, and interest alignment for every activity.

## 🚀 Getting Started

### Prerequisites

You will need the following Python libraries installed:

```bash
pip install requests icalendar
```

### Configuration

1. **API Key**: Obtain an API key from [OpenRouter](https://openrouter.ai/).
2. **Setup**: Open `travel_agent.ipynb` and enter your API key in the configuration cell:

```python
OPENROUTER_API_KEY = "your-api-key-here"
```

## 🛠️ Usage

1. **Set Your Preferences**: Edit the "Trip Inputs" cell with your desired trip details:
   - `destination`: e.g., "Paris, France"
   - `num_days`: Duration of your stay
   - `budget`: "low", "mid", or "luxury"
   - `interests`: List of tags (e.g., `["food", "art", "nightlife"]`)
   - `companions`: "solo", "couple", "family", or "group"
2. **Generate**: Run the notebook cells sequentially. The agent will call the AI to craft your perfect trip.
3. **Review**: Check the generated Markdown itinerary for restaurant names, landmarks, and hidden gems.
4. **Export**: The final cell generates a `travel_itinerary.ics` file. Import this into your preferred calendar app.

## 📦 Project Structure

- `travel_agent.ipynb`: The main Jupyter Notebook containing the agent logic and UI.
- `travel_itinerary.ics`: The exported calendar file (generated after running the notebook).
- `README.md`: Project documentation.

## 🛠️ Technologies Used

- **Python**: Core programming language.
- **OpenRouter API**: Interface for advanced LLMs (GPT-4o-mini).
- **iCalendar**: Library for generating standardized calendar files.
- **Jupyter**: Interactive environment for seamless experimentation.

---
*Created with ❤️ for travelers who want to explore more and plan less.*
