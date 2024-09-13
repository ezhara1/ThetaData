import streamlit as st
from datetime import date
from thetadata import ThetaClient, OptionReqType, OptionRight, DateRange, SecType, DataType, NoData
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go  # For scatter and candlestick charts

# Initialize the ThetaClient (assuming it doesn't require authentication for simplicity)
client = ThetaClient()

# Function to handle button actions for chart type
def set_chart_type(chart_type):
    st.session_state.chart_data_type = chart_type

# Check if the chart_data_type key exists in session_state, if not, initialize it for both stock and option charts
if 'chart_data_type_stock' not in st.session_state:
    st.session_state['chart_data_type_stock'] = 'Line'  # Default chart type for stock
if 'chart_data_type_option' not in st.session_state:
    st.session_state['chart_data_type_option'] = 'Line'  # Default chart type for options

if 'chart_data_type' not in st.session_state:
    st.session_state['chart_data_type'] = 'Price'

# Sidebar: Symbol Selection
with client.connect():
    symbols = client.get_roots(SecType.OPTION)
symbol = st.sidebar.selectbox("Select Symbol", symbols)

options = ["PUT", "CALL"]
option_type = st.sidebar.selectbox("Select Option Type", options)

# Sidebar: Expiration Date Selection based on selected Symbol
with client.connect():
    expirations = client.get_expirations(symbol).sort_values(ascending=False)
expiration = st.sidebar.selectbox("Select Expiration Date", expirations)

# Sidebar: Strike Price Selection based on selected Symbol and Expiration Date
with client.connect():
    strikes = client.get_strikes(symbol, expiration)
strike = st.sidebar.selectbox("Select Strike Price", strikes)

# Sidebar: Option to add more exercise date data
add_more_data = st.sidebar.radio("Add More Exercise Date Data?", ["No", "Yes"])

# Initialize variable for secondary exercise date selection
secondary_expiration = None
if add_more_data == "Yes":
    secondary_expiration = st.sidebar.selectbox("Select Additional Exercise Date", expirations, key='secondary_expiration')

# Sidebar: Date Range Selection for Historical Data
start_date = st.sidebar.date_input("Start Date", date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", date.today())

# Sidebar: Display Mode Selection for Option Data
display_mode = st.sidebar.radio("Display Mode", ['Chart', 'Table'])

# Fetch Historical Option Data for primary expiration
try:
    with client.connect():
        data_details = client.get_hist_option(
            req=OptionReqType.EOD,
            root=symbol,
            exp=expiration,
            strike=strike,
            right=OptionRight.CALL if option_type == "CALL" else OptionRight.PUT,
            date_range=DateRange(start_date, end_date)
        )
except (NoData, ValueError):
    st.write("No data available for the selected options.")
    data_details = None
    expiration = None

if data_details is not None and not data_details.empty:
    data_details['Expiration'] = expiration  # Assign expiration date directly

# Fetch for secondary expiration if selected
secondary_data_details = None
if secondary_expiration:
    try:
        with client.connect():
            secondary_data_details = client.get_hist_option(
                req=OptionReqType.EOD,
                root=symbol,
                exp=secondary_expiration,
                strike=strike,
                right=OptionRight.CALL if option_type == "CALL" else OptionRight.PUT,
                date_range=DateRange(start_date, end_date)
            )
    except NoData:
        st.write("No data available for the selected options.")
        secondary_data_details = None
        secondary_expiration = None

    if secondary_data_details is not None and not secondary_data_details.empty:
        secondary_data_details['Expiration'] = secondary_expiration  # Assign secondary expiration date directly

# Download stock quote data
stock_quote = yf.download(symbol, start=start_date, end=end_date)
stock_quote.reset_index(inplace=True)

ticker = yf.Ticker(symbol)
info = ticker.info
stock_name = info.get("longName", "")

# Main window: Show the symbol name and latest price
if not stock_quote.empty:
    latest_price = stock_quote.iloc[-1]['Close']
else:
    latest_price = 0  # Fallback if stock_quote is empty

st.write(f"Symbol: {symbol} - {stock_name} - Latest Price: {latest_price:.2f}")

st.write("Stock Price Chart")

button_col1, button_col2, button_col3 = st.columns(3)

with button_col1:
    if st.button('Line', key='line_stock'):
        st.session_state.chart_data_type_stock = 'Line'

with button_col2:
    if st.button('Scatter', key='scatter_stock'):
        st.session_state.chart_data_type_stock = 'Scatter'

with button_col3:
    if st.button('Candlestick', key='candlestick_stock'):
        st.session_state.chart_data_type_stock = 'Candlestick'

chart_type_stock = st.session_state.chart_data_type_stock

# Display the stock price chart based on selected chart type
if chart_type_stock == "Line":
    st.line_chart(stock_quote.set_index('Date')['Close'])
elif chart_type_stock == "Scatter":
    fig_scatter = go.Figure(data=[go.Scatter(x=stock_quote['Date'], y=stock_quote['Close'], mode='markers')])
    st.plotly_chart(fig_scatter)
elif chart_type_stock == "Candlestick":
    fig_candlestick = go.Figure(data=[go.Candlestick(x=stock_quote['Date'],
                                                     open=stock_quote['Open'], high=stock_quote['High'],
                                                     low=stock_quote['Low'], close=stock_quote['Close'])])
    fig_candlestick.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig_candlestick)

# Combine data_details and secondary_data_details if both are available
combined_data = pd.DataFrame()
if data_details is not None and not data_details.empty:
    if secondary_data_details is not None and not secondary_data_details.empty:
        combined_data = pd.concat([data_details, secondary_data_details])
    else:
        combined_data = data_details.copy()

if not combined_data.empty:
    combined_data['Date'] = pd.to_datetime(combined_data['date'])  # Use actual column name 'date'

    # Set 'Expiration' column as string for plotting
    combined_data['Expiration'] = combined_data['Expiration'].astype(str)

    st.write(f"Option {st.session_state.chart_data_type} Chart")

    if display_mode == 'Chart':
        # Buttons to select chart type
        opt_button_col1, opt_button_col2, opt_button_col3 = st.columns(3)

        with opt_button_col1:
            if st.button('Line', key='line_option'):
                st.session_state.chart_data_type_option = 'Line'

        with opt_button_col2:
            if st.button('Scatter', key='scatter_option'):
                st.session_state.chart_data_type_option = 'Scatter'

        with opt_button_col3:
            if st.button('Candlestick', key='candlestick_option'):
                st.session_state.chart_data_type_option = 'Candlestick'

        chart_type_option = st.session_state.chart_data_type_option

        # Pivot the combined data for charting
        data_type = 'close' if st.session_state.chart_data_type == 'Price' else 'volume'
        chart_data = combined_data.pivot_table(index='Date', columns='Expiration', values=data_type)

        if chart_type_option == "Line":
            st.line_chart(chart_data)
        elif chart_type_option == "Scatter":
            fig_scatter_option = go.Figure()
            for exp in chart_data.columns:
                fig_scatter_option.add_trace(go.Scatter(
                    x=chart_data.index,
                    y=chart_data[exp],
                    mode='markers',
                    name=f'Expiration {exp}'
                ))
            st.plotly_chart(fig_scatter_option)
        elif chart_type_option == "Candlestick":
            # Handle candlestick chart for each expiration separately
            for exp in combined_data['Expiration'].unique():
                exp_data = combined_data[combined_data['Expiration'] == exp]
                fig_candlestick_option = go.Figure(data=[go.Candlestick(
                    x=exp_data['Date'],
                    open=exp_data['open'],
                    high=exp_data['high'],
                    low=exp_data['low'],
                    close=exp_data['close']
                )])
                fig_candlestick_option.update_layout(
                    xaxis_rangeslider_visible=False,
                    title=f"Candlestick Chart for Expiration {exp}"
                )
                st.plotly_chart(fig_candlestick_option)

        # Buttons to select data type (Price or Volume)
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button('Price', key='price'):
                set_chart_type('Price')
        with col2:
            if st.button('Volume', key='volume'):
                set_chart_type('Volume')

    elif display_mode == 'Table':
        # Show data in a table format
        st.write("Option Data Table")
        st.dataframe(combined_data)
else:
    st.write("No option data available for the selected criteria.")

