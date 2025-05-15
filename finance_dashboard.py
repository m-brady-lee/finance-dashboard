import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import linregress
import numpy as np
import calendar
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import seaborn as sns
import random

### FOR LOCAL HOSTING 
# Read the CSV file
df = pd.read_csv('Test Financial Data.csv')
###

# Process the Date and Amount columns
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df['Amount'] = pd.to_numeric(df['Amount'].replace({',': '', '$': ''}, regex=True), errors='coerce')
df = df.dropna(subset=['Amount', 'Date'])
df['Description (Transaction Detail)'] = df['Description (Transaction Detail)'].astype(str)

# Filter income and expense data
income_data = df[df['Category'] == 'INCOME']

expenses_data = df[df['Category'] == 'EXPENSES'].copy()
expenses_data['Amount'] = expenses_data['Amount'] * -1  # Make amounts positive

debt_data = df[df['Category'] == 'DEBT'].copy()
debt_data['Amount'] = debt_data['Amount'] * -1  # Make amounts positive

payment_data = df[df['Category'] == 'PAYMENTS'].copy()
payment_data['Amount'] = payment_data['Amount'] * -1  # Make amounts positive

utilities_data = df[df['Category'] == 'UTILITIES'].copy()
utilities_data['Amount'] = utilities_data['Amount'] * -1  # Make amounts positive

insurance_data = df[df['Category'] == 'INSURANCE'].copy()
insurance_data['Amount'] = insurance_data['Amount'] * -1  # Make amounts positive

all_expense_data = df[df['Category'].isin(['EXPENSES', 'PAYMENTS', 'UTILITIES', 'INSURANCE'])].copy()
all_expense_data['Amount'] = all_expense_data['Amount'] * -1  # Make amounts positive


def generate_master_palette(n_colors):
    # Use a mix of Seaborn palettes for better variety
    base_palettes = [
        sns.color_palette("tab20", 20),
        sns.color_palette("Set3", 12),
        sns.color_palette("Paired", 12),
        sns.color_palette("Dark2", 8),
        sns.color_palette("Pastel1", 9),
        sns.color_palette("Pastel2", 8),
        sns.color_palette("Set2", 8),
        sns.color_palette("Accent", 8),
        sns.color_palette("Set1", 9),
        sns.color_palette("tab10", 9)
    ]

    # Flatten and convert to hex
    all_colors = [mcolors.to_hex(color) for palette in base_palettes for color in palette]

    # Shuffle and remove duplicates
    unique_colors = list(dict.fromkeys(all_colors))
    random.seed(22)
    random.shuffle(unique_colors)

    # Pad with matplotlib's turbo colormap if needed
    if len(unique_colors) < n_colors:
        turbo_colors = [mcolors.to_hex(plt.cm.turbo(i / n_colors)) for i in range(n_colors)]
        unique_colors.extend(turbo_colors)

    return unique_colors[:n_colors]


# Create a master palette
master_palette = generate_master_palette(500)


# Split into four groups (40 each)
income_colors_list = master_palette[:40]
debt_colors_list = master_palette[40:80]
cash_colors_list = master_palette[80:120]
expense_colors_list = master_palette[2:500:3]

def assign_colors(accounts, color_list):
    return {acc: color_list[i % len(color_list)] for i, acc in enumerate(accounts)}


income_colors = assign_colors(income_data['Sub-Category (Account)'].unique(), income_colors_list)
debt_colors = assign_colors(debt_data['Sub-Category (Account)'].unique(), debt_colors_list)
cash_colors = assign_colors(df[df['Category'] == 'CASH_ON_HAND']['Sub-Category (Account)'].unique(), cash_colors_list)
expense_colors = assign_colors(all_expense_data['Sub-Category (Account)'].unique(), expense_colors_list)


# Sorted list of all income categories by total amount
income_type_sorted = (
    income_data.groupby('Sub-Category (Account)')['Amount']
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)

# Sorted list of all expense categories by category (payments, utilities & insurance, expenses) then by total amount
sorted_payments = (
    payment_data.groupby('Sub-Category (Account)')['Amount']
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)

sorted_utilities_insurance = (
    pd.concat([utilities_data, insurance_data])
    .groupby('Sub-Category (Account)')['Amount']
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)


sorted_expenses = (
    expenses_data.groupby('Sub-Category (Account)')['Amount']
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)

# Combine all sorted categories preserving the desired order

# expense_categories_sorted = pd.concat([
#     sorted_payments,
#     sorted_utilities_insurance,
#     sorted_expenses
# ]).index.tolist()

expense_categories_sorted = (
    all_expense_data.groupby('Sub-Category (Account)')['Amount']
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)

# Save for use in Dash stores
grouped_expense_categories = {
    'Debt Payments': sorted_payments,
    'Utilities & Insurance': sorted_utilities_insurance,
    'Categories': sorted_expenses
}

# Create the Dash app
app = dash.Dash(__name__)
app.config.suppress_callback_exceptions = True  # This suppresses warnings for pages that aren't loaded yet

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

def create_empty_figure(title="Empty Chart", message="No data to display"):
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[{
            'text': message,
            'xref': 'paper',
            'yref': 'paper',
            'showarrow': False,
            'font': {'size': 16}
        }],
        height=400
    )
    return fig


# Get all unique years
available_years = sorted(df['Date'].dt.year.dropna().unique().astype(str))

# Layout of the Dash app
income_vs_expenses_layout = (html.Div([
    # Display Options and Year Filter side-by-side, both centered in their columns
    html.Div([

        # Navigation links
        html.Div([
            dcc.Link('Income vs Expenses', href='/income-expense', style={'marginRight': '20px'}),
            dcc.Link('Yearly Summary', href='/yearly-summary')
        ], style={
            'textAlign': 'center',
            'marginBottom': '10px'
        }),
        html.Div([
            html.H1("Income vs Expenses", style={'textAlign': 'center', 'marginBottom': '2px'}),
        ]),

        html.Div([
            # Left column (Display Options)
            html.Div([
                html.Label("Display Options", style={
                    'fontWeight': 'bold',
                    'fontSize': '16px',
                    'marginBottom': '6px',
                    'textAlign': 'center',
                    'display': 'block'
                }),
                # Checklist for Income and Expenses
                dcc.Checklist(
                    id='show-options',
                    options=[
                        {'label': 'Income', 'value': 'income'},
                        {'label': 'Expenses', 'value': 'expense'},
                    ],
                    value=['income', 'expense'],
                    style={
                        'display': 'flex',
                        'justifyContent': 'center',
                        'flexWrap': 'wrap',
                        'gap': '15px'
                    }
                ),
                # Radio buttons for line display type
                html.Div([
                    dcc.RadioItems(
                        id='line-options',
                        options=[
                            {'label': 'Trend Lines', 'value': 'regression'},
                            {'label': 'Average Lines', 'value': 'average'}
                        ],
                        value='regression',
                        labelStyle={'display': 'inline-block', 'marginRight': '15px'},
                        style={'textAlign': 'center'}
                    )
                ], style={'marginTop': '2px'})
                ,
                dcc.RadioItems(
                    id='view-mode',
                    options=[
                        {'label': 'By Month', 'value': 'month'},
                        {'label': 'By Year', 'value': 'year'}
                    ],
                    value='month',
                    labelStyle={'display': 'inline-block', 'marginRight': '12px'},
                    style={'textAlign': 'center', 'marginTop': '2px'}
                )
            ], style={'flex': '1'}),

            # Right column (Select Timeframe)
            html.Div([
                html.Label("Select Timeframe", style={
                    'fontWeight': 'bold',
                    'fontSize': '16px',
                    'marginBottom': '6px',
                    'textAlign': 'center',
                    'display': 'block'
                }),
                dcc.Checklist(
                    id='year-filter',
                    options=[{'label': year, 'value': year} for year in available_years],
                    value=available_years,
                    style={
                        'display': 'flex',
                        'justifyContent': 'center',
                        'flexWrap': 'wrap',
                        'gap': '10px'
                    }
                ),
                html.Div([
                    html.Button("Select All", id="select-all-years", n_clicks=0),
                    html.Button("Clear All", id="clear-all-years", n_clicks=0),
                    dcc.Store(id="all-year-options", data=available_years)
                ], style={'display': 'flex', 'justifyContent': 'center', 'gap': '10px', 'marginTop': '5px'})
            ], style={'flex': '1'})
        ], style={
            'display': 'flex',
            'gap': '0px',
            'justifyContent': 'space-between',
            'alignItems': 'center'
        })

    ], style={
        'position': 'sticky',
        'top': '0',
        'zIndex': '1000',
        'backgroundColor': 'white',
        'padding': '15px 20px',
        'borderBottom': '1px solid #ccc'
    }),

    dcc.Graph(id='income-expense-graph'),

    # Container for the Income Account and Expense Sub-Category Filters
    # Side-by-side Income and Expense Filters
    html.Div([
        html.Div(style={'width': '60px'}),
        # Income filter
        html.Div([
            html.Label("Income Source", id='account-filter-title', style={
                'fontWeight': 'bold',
                'fontSize': '16px',
                'marginBottom': '6px',
                'display': 'block',
                'textAlign': 'center'
            }),
            dcc.Checklist(
                id='account-filter',
                options=[{'label': cat, 'value': cat} for cat in income_type_sorted],
                value=income_type_sorted,
                style={
                    'display': 'flex',
                    'flexWrap': 'wrap',
                    'gap': '10px',
                    'marginTop': '10px',
                    'justifyContent': 'left',
                    'minWidth': '200px'
                }
            ),
            html.Div([
                    html.Button("Select All", id="select-all-income-filter", n_clicks=0),
                    html.Button("Clear All", id="clear-all-income-filter", n_clicks=0),
                    dcc.Store(id='account-filter-options-store')
                ], style={'display': 'flex', 'gap': '10px', 'marginTop': '10px', 'justifyContent': 'left'})
        ], id='account-filter-container', style={'flex': '1'}
        ),
        html.Div(style={'width': '50px'}),

        # Expense Filter Section
        html.Div([
            html.Label("Expense Source", id='expense-filter-title', style={
                'fontWeight': 'bold',
                'fontSize': '16px',
                'marginBottom': '0px',
                'display': 'block',
                'textAlign': 'center',

            }),

            html.Div([
                html.P("Debt Payments", style={'fontWeight': 'bold', 'marginBottom': '6px'}),
                dcc.Checklist(
                    id='payments-filter',
                    options=[{'label': cat, 'value': cat} for cat in sorted_payments],
                    value=sorted_payments,
                    inline=True,
                    style={
                        'display': 'flex',
                        'flexWrap': 'wrap',
                        'gap': '10px',
                        'justifyContent': 'left',
                        'maxWidth': '900px',
                        'marginTop': '0px'
                    }
                ),
                html.Div([
                    html.Button("Select All", id="select-all-payments", n_clicks=0),
                    html.Button("Clear All", id="clear-all-payments", n_clicks=0),
                    dcc.Store(id='payments-filter-options-store', data=sorted_payments)
                ], style={'display': 'flex', 'gap': '10px', 'marginTop': '6px'})
            ], style={'marginBottom': '15px', 'maxWidth': '900px'}),


            html.Div([
                html.P("General Categories", style={'fontWeight': 'bold', 'marginBottom': '6px'}),
                dcc.Checklist(
                    id='expense-category-filter',
                    options=[{'label': cat, 'value': cat} for cat in sorted_expenses],
                    value=sorted_expenses,
                    inline=True,
                    style={
                        'display': 'flex',
                        'flexWrap': 'wrap',
                        'gap': '10px',
                        'justifyContent': 'left',
                        'maxWidth': '800px'
                    }
                ),
                html.Div([
                        html.Button("Select All", id="select-all-categories", n_clicks=0),
                        html.Button("Clear All", id="clear-all-categories", n_clicks=0),
                        dcc.Store(id='expense-category-filter-options-store', data=sorted_expenses)
                    ], style={'display': 'flex', 'gap': '10px', 'marginTop': '6px'})
            ], style={'marginBottom': '15px', 'maxWidth': '800px'}),

            html.Div([
                html.P("Utilities & Insurance", style={'fontWeight': 'bold', 'marginBottom': '6px'}),
                dcc.Checklist(
                    id='utilities-insurance-filter',
                    options=[{'label': cat, 'value': cat} for cat in sorted_utilities_insurance],
                    value=sorted_utilities_insurance,
                    inline=True,
                    style={
                        'display': 'flex',
                        'flexWrap': 'wrap',
                        'gap': '10px',
                        'justifyContent': 'left',
                        'maxWidth': '800px'
                    }
                ),
                html.Div([
                    html.Button("Select All", id="select-all-utilities", n_clicks=0),
                    html.Button("Clear All", id="clear-all-utilities", n_clicks=0),
                    dcc.Store(id='utilities-insurance-filter-options-store', data=sorted_utilities_insurance)
                ], style={'display': 'flex', 'gap': '10px', 'marginTop': '6px'})
            ], style={'marginBottom': '15px', 'maxWidth': '800px'}),

            html.Div([
                html.Button("Select All (All Categories)", id="select-all-expenses-master", n_clicks=0),
                html.Button("Clear All (All Categories)", id="clear-all-expenses-master", n_clicks=0)
            ], style={
                'display': 'flex',
                'gap': '10px',
                'justifyContent': 'left',
                'marginTop': '10px'
            })

        ], id='expense-filter-container', style={
            'flex': '1',
            'minWidth': '300px',
            'maxWidth': '300px',
            'marginLeft': '40px'
        })

    ], style={'display': 'flex', 'gap': '40px', 'alignItems': 'flex-start', 'padding': '20px'}),
    html.Br(),
    html.Br(),
    html.Br(),
    html.Br()
], style={'padding': '20px','marginTop': '0px'}))

@app.callback(
    Output('year-filter', 'value', allow_duplicate=True),
    [Input('select-all-years', 'n_clicks'),
     Input('clear-all-years', 'n_clicks')],
    State('all-year-options', 'data'),
    prevent_initial_call=True
)
def toggle_year_selection(n_select, n_clear, all_years):
    ctx = dash.callback_context
    if not ctx.triggered or all_years is None:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'select-all-years':
        return all_years
    elif button_id == 'clear-all-years':
        return []
    return dash.no_update

@app.callback(
    [Output('payments-filter', 'options'),
     Output('payments-filter', 'value'),
     Output('payments-filter-options-store', 'data'),
     Output('utilities-insurance-filter', 'options'),
     Output('utilities-insurance-filter', 'value'),
     Output('utilities-insurance-filter-options-store', 'data'),
     Output('expense-category-filter', 'options'),
     Output('expense-category-filter', 'value'),
     Output('expense-category-filter-options-store', 'data')],
    Input('year-filter', 'value')
)
def update_expense_filters_from_year_filter(selected_years):
    if not selected_years:
        return ([], [], [], [], [], [], [], [], [])

    selected_years_int = [int(y) for y in selected_years]

    # Payments
    filtered_payments = payment_data[payment_data['Date'].dt.year.isin(selected_years_int)]
    payments_sorted = (
        filtered_payments.groupby('Sub-Category (Account)')['Amount']
        .sum().sort_values(ascending=False).index.tolist()
    )
    payments_options = [{'label': cat, 'value': cat} for cat in payments_sorted]

    # Utilities & Insurance
    filtered_ui = pd.concat([utilities_data, insurance_data])
    filtered_ui = filtered_ui[filtered_ui['Date'].dt.year.isin(selected_years_int)]
    ui_sorted = (
        filtered_ui.groupby('Sub-Category (Account)')['Amount']
        .sum().sort_values(ascending=False).index.tolist()
    )
    ui_options = [{'label': cat, 'value': cat} for cat in ui_sorted]

    # General Expenses
    filtered_expenses = expenses_data[expenses_data['Date'].dt.year.isin(selected_years_int)]
    expenses_sorted = (
        filtered_expenses.groupby('Sub-Category (Account)')['Amount']
        .sum().sort_values(ascending=False).index.tolist()
    )
    expense_options = [{'label': cat, 'value': cat} for cat in expenses_sorted]

    return (
        payments_options, payments_sorted, payments_sorted,
        ui_options, ui_sorted, ui_sorted,
        expense_options, expenses_sorted, expenses_sorted
    )


@app.callback(
    [Output('account-filter', 'options'),
     Output('account-filter', 'value'),
     Output('account-filter-options-store', 'data')],
    Input('year-filter', 'value')
)
def update_income_accounts_from_year_filter(selected_years):
    if not selected_years:
        return [], [], []

    selected_years_int = [int(y) for y in selected_years]
    filtered_income = income_data[income_data['Date'].dt.year.isin(selected_years_int)]

    if filtered_income.empty:
        return [], [], []

    totals = (
        filtered_income
        .groupby('Sub-Category (Account)')['Amount']
        .sum()
        .sort_values(ascending=False)
    )

    options = [{'label': acc, 'value': acc} for acc in totals.index]
    values = list(totals.index)

    return options, values, values


@app.callback(
    [Output('payments-filter', 'value', allow_duplicate=True),
     Output('utilities-insurance-filter', 'value', allow_duplicate=True),
     Output('expense-category-filter', 'value', allow_duplicate=True)],
    [Input('select-all-expenses-master', 'n_clicks'),
     Input('clear-all-expenses-master', 'n_clicks')],
    [State('payments-filter-options-store', 'data'),
     State('utilities-insurance-filter-options-store', 'data'),
     State('expense-category-filter-options-store', 'data')],
    prevent_initial_call=True
)
def toggle_all_expense_categories(select_all_clicks, clear_all_clicks,
                                  payments_options, utilities_options, category_options):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'select-all-expenses-master':
        return payments_options, utilities_options, category_options
    elif button_id == 'clear-all-expenses-master':
        return [], [], []

    return dash.no_update



@app.callback(
    Output('payments-filter', 'value', allow_duplicate=True),
    [Input('select-all-payments', 'n_clicks'),
     Input('clear-all-payments', 'n_clicks')],
    State('payments-filter-options-store', 'data'),
    prevent_initial_call=True
)
def toggle_payments_filter(select_all_clicks, clear_all_clicks, all_options):
    ctx = dash.callback_context
    if not ctx.triggered or all_options is None:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'select-all-payments':
        return all_options
    elif button_id == 'clear-all-payments':
        return []
    return dash.no_update

@app.callback(
    Output('utilities-insurance-filter', 'value', allow_duplicate=True),
    [Input('select-all-utilities', 'n_clicks'),
     Input('clear-all-utilities', 'n_clicks')],
    State('utilities-insurance-filter-options-store', 'data'),
    prevent_initial_call=True
)
def toggle_utilities_filter(select_all_clicks, clear_all_clicks, all_options):
    ctx = dash.callback_context
    if not ctx.triggered or all_options is None:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'select-all-utilities':
        return all_options
    elif button_id == 'clear-all-utilities':
        return []
    return dash.no_update

@app.callback(
    Output('expense-category-filter', 'value', allow_duplicate=True),
    [Input('select-all-categories', 'n_clicks'),
     Input('clear-all-categories', 'n_clicks')],
    State('expense-category-filter-options-store', 'data'),
    prevent_initial_call=True
)
def toggle_categories_filter(select_all_clicks, clear_all_clicks, all_options):
    ctx = dash.callback_context
    if not ctx.triggered or all_options is None:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'select-all-categories':
        return all_options
    elif button_id == 'clear-all-categories':
        return []
    return dash.no_update


@app.callback(
    Output('account-filter', 'value', allow_duplicate=True),
    [Input('select-all-income-filter', 'n_clicks'),
     Input('clear-all-income-filter', 'n_clicks')],
    State('account-filter-options-store', 'data'),
    prevent_initial_call=True
)
def toggle_income_filter(select_all_clicks, clear_all_clicks, all_options):
    ctx = dash.callback_context
    if not ctx.triggered or not all_options:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'select-all-income-filter':
        return all_options
    elif button_id == 'clear-all-income-filter':
        return []
    return dash.no_update


@app.callback(
    Output('income-expense-graph', 'figure'),
    [Input('account-filter', 'value'),
     Input('payments-filter', 'value'),
     Input('utilities-insurance-filter', 'value'),
     Input('expense-category-filter', 'value'),
     Input('year-filter', 'value'),
     Input('show-options', 'value'),
     Input('line-options', 'value'),
     Input('view-mode', 'value')]
)
def update_graph(selected_accounts, payments, utilities, categories, selected_years, show_options, line_option, view_mode):
    selected_expenses = payments + utilities + categories

    # Filter income data based on selected accounts
    filtered_income_data = income_data[income_data['Sub-Category (Account)'].isin(selected_accounts)]

    if not selected_years or not selected_accounts or not selected_expenses or not show_options:
        return create_empty_figure(title='Income vs Expenses', message="Please select at least one filter option.")

    # Filter expense data based on combined selections
    filtered_expense_data = all_expense_data[all_expense_data['Sub-Category (Account)'].isin(selected_expenses)]

    # Filter by selected years
    if 'All' not in selected_years:
        selected_years_int = [int(year) for year in selected_years]
        filtered_income_data = filtered_income_data[filtered_income_data['Date'].dt.year.isin(selected_years_int)]
        filtered_expense_data = filtered_expense_data[
            filtered_expense_data['Date'].dt.year.isin(selected_years_int)]

    if view_mode == 'year':
        # Group by year
        income_by_period = filtered_income_data.groupby(filtered_income_data['Date'].dt.year)['Amount'].sum()
        expense_by_period = filtered_expense_data.groupby(filtered_expense_data['Date'].dt.year)['Amount'].sum()
        period_labels = income_by_period.index.astype(str)
    else:
        # Group by year and month
        income_by_period = \
        filtered_income_data.groupby([filtered_income_data['Date'].dt.year, filtered_income_data['Date'].dt.month])[
            'Amount'].sum()
        expense_by_period = \
        filtered_expense_data.groupby([filtered_expense_data['Date'].dt.year, filtered_expense_data['Date'].dt.month])[
            'Amount'].sum()
        period_labels = pd.to_datetime(income_by_period.index.map(lambda x: f"{x[0]}-{x[1]:02d}"))

    # Combine income and expenses
    combined_df = pd.DataFrame({
        'Income': income_by_period,
        'Expenses': expense_by_period
    }).fillna(0)

    income_avg = combined_df['Income'].mean()
    expense_avg = combined_df['Expenses'].mean()

    # Regression lines
    x = np.arange(len(combined_df))
    slope_income, intercept_income, *_ = linregress(x, combined_df['Income'])
    slope_expense, intercept_expense, *_ = linregress(x, combined_df['Expenses'])
    income_trend = slope_income * x + intercept_income
    expense_trend = slope_expense * x + intercept_expense


    # Group by year and month
    income_by_month = filtered_income_data.groupby([filtered_income_data['Date'].dt.year, filtered_income_data['Date'].dt.month])['Amount'].sum()
    expense_by_month = filtered_expense_data.groupby([filtered_expense_data['Date'].dt.year, filtered_expense_data['Date'].dt.month])['Amount'].sum()

    # Combine into a single dataframe
    income_vs_expense_by_month = pd.DataFrame({
        'Income': income_by_month,
        'Expenses': expense_by_month
    }).fillna(0)

    # Create datetime index
    income_vs_expense_by_month['Year-Month'] = pd.to_datetime(income_vs_expense_by_month.index.map(lambda x: f"{x[0]}-{x[1]:02d}"))

    # Prepare regression lines for filtered data
    x = np.arange(len(income_vs_expense_by_month))
    slope_income, intercept_income, _, _, _ = linregress(x, income_vs_expense_by_month['Income'])
    slope_expenses, intercept_expenses, _, _, _ = linregress(x, income_vs_expense_by_month['Expenses'])

    income_regression_line = slope_income * x + intercept_income
    expenses_regression_line = slope_expenses * x + intercept_expenses

    # Create the interactive plot with Plotly
    fig = go.Figure()

    if 'income' in show_options:
        fig.add_trace(go.Bar(
            x=period_labels,
            y=combined_df['Income'],
            name='Income',
            marker_color='green',
            opacity=0.7,
            hovertemplate='%{x|%b %Y}<br>%{fullData.name}: $%{y:,.0f}<extra></extra>'

        ))
        if line_option == 'regression':
            # Income regression line
            fig.add_trace(go.Scatter(
                x=period_labels,
                y=income_trend,
                mode='lines',
                name='Income Trend',
                line=dict(color='darkgreen', dash='dash'),
                hovertemplate='$%{y:,.0f}<extra></extra>'
            ))
        if line_option == 'average':
            # Income average line
            fig.add_trace(go.Scatter(
                x=period_labels,
                y=[income_avg] * len(period_labels),
                mode='lines',
                name='Income Avg',
                line=dict(color='darkgreen', dash='dot'),
                hovertemplate='Average Income: $%{y:,.0f}<extra></extra>'
            ))

    if 'expense' in show_options:
        fig.add_trace(go.Bar(
            x=period_labels,
            y=combined_df['Expenses'],
            name='Expenses',
            marker_color='red',
            opacity=0.5,
            hovertemplate='%{x|%b %Y}<br>%{fullData.name}: $%{y:,.0f}<extra></extra>'

        ))
        if line_option == 'regression':
            # Expense regression line
            fig.add_trace(go.Scatter(
                x=period_labels,
                y=expense_trend,
                mode='lines',
                name='Expense Trend',
                line=dict(color='darkred', dash='dash'),
                hovertemplate='$%{y:,.0f}<extra></extra>'

            ))
        if line_option == 'average':
            # Expense average line
            fig.add_trace(go.Scatter(
                x=period_labels,
                y=[expense_avg] * len(period_labels),
                mode='lines',
                name='Expense Avg',
                line=dict(color='darkred', dash='dot'),
                hovertemplate='Average: $%{y:,.0f}<extra></extra>'
            ))

    fig.update_layout(
        title='Income vs Expenses',
        xaxis_title='Year' if view_mode == 'year' else 'Year-Month',
        yaxis_title='Amount ($)',
        barmode='overlay',
        height=600
    )

    return fig


# Callback to hide/show the income and expense filters and their titles based on the respective toggles
@app.callback(
    [Output('account-filter-container', 'style'),
     Output('account-filter-title', 'style'),
     Output('expense-filter-container', 'style'),
     Output('expense-filter-title', 'style')],
    [Input('show-options', 'value')]
)
def toggle_filters(show_options):
    base_label_style = {
        'fontWeight': 'bold',
        'fontSize': '16px',
        'marginBottom': '6px',
        'textAlign': 'center',
        'display': 'block'
    }

    if 'income' not in show_options:
        income_filter_style = {'display': 'none'}
        income_filter_title_style = {'display': 'none'}
    else:
        income_filter_style = {'display': 'block'}
        income_filter_title_style = base_label_style

    if 'expense' not in show_options:
        expense_filter_style = {'display': 'none'}
        expense_filter_title_style = {'display': 'none'}
    else:
        expense_filter_style = {'display': 'block'}
        expense_filter_title_style = base_label_style

    return income_filter_style, income_filter_title_style, expense_filter_style, expense_filter_title_style


# Layout for the Yearly Summary page
yearly_summary_layout = html.Div([
    html.Div([
        # Navigation links
        html.Div([
            html.A('Income vs Expenses', href='/income-expense', style={'marginRight': '20px'}),
            html.A('Yearly Summary', href='/yearly-summary')
        ], style={
            'textAlign': 'center',
            'marginBottom': '10px'
        }),

        html.Div(id='yearly-summary-title'),
        html.Div(
            id='year-month-radio-container',
            style={'display': 'none'},  # <-- hides it!
            children=[
                html.Div([
                    html.Label('Select Year', style= {'fontWeight': 'bold'}),
                    dcc.RadioItems(
                        id='year-radio',
                        options=[{'label': str(year), 'value': year} for year in sorted(df['Date'].dt.year.unique())],
                        value=df['Date'].dt.year.max(),
                        inline=True,
                        style={'justifyContent': 'center'}
                    )
                ], style={
                    'textAlign': 'center',
                    'marginTop': '10px',
                    'marginBottom': '5px'
                }),
                html.Div([
                    html.Label('Select Month', style= {'fontWeight': 'bold'}),
                    dcc.RadioItems(
                        id='month-radio',
                        options=[{'label': m, 'value': i} for i, m in enumerate(
                            ['Full Year', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        )],
                        value=0,  # Default to "Full Year"
                        inline=True,
                        style={'justifyContent': 'center'}
                    )
                ], style={
                    'textAlign': 'center',
                    'marginTop': '0px',
                    'marginBottom': '0px'
                })
            ]
        ),
        html.Div([
             html.Div([
                dcc.Dropdown(
                    id='selected-month-dropdown',
                    options=[
                        {'label': 'Full Year', 'value': 0},
                        {'label': 'January', 'value': 1},
                        {'label': 'February', 'value': 2},
                        {'label': 'March', 'value': 3},
                        {'label': 'April', 'value': 4},
                        {'label': 'May', 'value': 5},
                        {'label': 'June', 'value': 6},
                        {'label': 'July', 'value': 7},
                        {'label': 'August', 'value': 8},
                        {'label': 'September', 'value': 9},
                        {'label': 'October', 'value': 10},
                        {'label': 'November', 'value': 11},
                        {'label': 'December', 'value': 12},
                    ],
                    clearable=False,
                    style={
                        'width': '100px',
                        'padding': '1px 1px',
                        'border': '1px solid #ccc',
                        'textAlign': 'left',
                        'whiteSpace': 'nowrap',
                        'fontFamily': 'arial',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'right'
                    }
                )
            ]),

            html.Div('-', style={
                'width': '30px',
                'textAlign': 'center',
                'fontFamily': 'arial',
                'fontWeight': 'bold',
                'color': '#555',
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'center'
            }),

            html.Div(
                dcc.Dropdown(
                    id='selected-year-dropdown',
                    options=[],  # dynamically populated
                    value=None,  # will be set based on current selected year
                    clearable=False,
                     style={
                        'width': '80px',
                        'padding': '1px 1px',
                        'border': '1px solid #ccc',
                        'textAlign': 'left',
                        'whiteSpace': 'nowrap',
                        'fontFamily': 'arial',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'right'
                     })
            )
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'gap': '0px',
            'marginBottom': '2px',
        })
        ,
        html.Div([
            dcc.Store(id='month-change-store'),
            dcc.Store(id='year-change-store'),
            html.Div([
                html.Button('First', id='first-button', n_clicks=0, title='Go to the first year of data', style={
                    'margin': '0 4px',
                    'padding': '6px 12px',
                    'fontSize': '14px'
                }),
                html.Button('<<', id='prev-year-button', n_clicks=0, title='Go to the previous year of data', disabled=False),
                html.Button("<", id="prev-month-button", n_clicks=0, title='Go to the previous month of data', disabled=False),
                html.Button(">", id="next-month-button", n_clicks=0, title='Go to the next month of data'),
                html.Button(">>", id="next-year-button", n_clicks=0, title='Go to the next year of data'),
                html.Button("Latest", id="latest-button", n_clicks=0, title='Go to most recent year of data')
            ], style={
                'display': 'flex',
                'justifyContent': 'center',
                'gap': '10px',
                'marginTop': '8px',
                'marginBottom': '0px'
            })
        ])
        ,



    ], style={
        'textAlign': 'center',
        'position': 'sticky',
        'top': '0',
        'backgroundColor': 'white',
        'zIndex': '1000',
        'padding': '15px 0',
        'borderBottom': '1px solid #ccc'
    }),

    # FINANCIAL OVERVIEW SECTION
    html.Div([
        html.H2("Financial Overview", style={'textAlign': 'center', 'marginBottom': '20px'}),

        html.Div([
            # === Ratio Gauges ===
            html.Div([
                html.Div([
                    dcc.Graph(id='income-to-expense-gauge', config={'displayModeBar': False})
                ], style={'flex': '1', 'padding': '0px'}),
                html.Div([
                    dcc.Graph(id='debt-to-income-gauge', config={'displayModeBar': False})
                ], style={'flex': '1', 'padding': '0px'}),
                html.Div([
                    dcc.Graph(id='cash-to-debt-gauge', config={'displayModeBar': False})
                ], style={'flex': '1', 'padding': '0px'})

            ], style={'display': 'flex', 'justifyContent': 'center', 'gap': '0px', 'marginBottom': '0px'})
        ]),

        # === Financial Snapshot Row ===
        html.Div([
            # === Income Section ===
            html.Div([
                # First row: Total Income (larger font)
                html.Div([
                    html.P("Total Income", style={
                        'fontWeight': 'bold',
                        'fontSize': '22px',
                        'marginBottom': '4px'
                    }),
                    html.Label(id='income-total-display', style={
                        'fontSize': '42px'
                    })
                ], style={'textAlign': 'center', 'marginBottom': '0px'}),

                # Second row: Monthly Avg and % Change
                html.Div([
                    # Monthly Average
                    html.Div([
                        html.P("Monthly Average", style={'fontWeight': 'bold', 'minWidth': '120px', 'marginBottom': '4px'}),
                        html.Label(id='income-avg-display', style={'fontSize': '20px'})
                    ], id='income-avg-container', style={'textAlign': 'center'}),

                    # % Change
                    html.Div([
                        html.P(id='income-change-title', children="% Income Change (YTD):",
                               style={'fontWeight': 'bold', 'minWidth': '180px', 'textAlign': 'left', 'marginBottom': '4px'}),
                        html.Div([
                            html.Label(id='income-change-display', style={'fontSize': '18px', 'minWidth': '100px'}),
                            html.Label(id='income-change-amount', style={'fontSize': '14px', 'color': '#777', 'marginLeft': '10px'})
                        ])
                    ], style={'textAlign': 'center', 'marginLeft': '20px', 'minWidth':'100px'})
                ], style={
                    'display': 'flex',
                    'justifyContent': 'center',
                    'gap': '0px'
                })
            ], style={
                'flex': '1',
                'padding': '30px 0',
                'minWidth': '300px',
                'flexGrow': 1
            }),

            # === Expense Section ===
            html.Div([
                # First row: Total Expenses (larger font)
                html.Div([
                    html.P("Total Expenses", style={
                        'fontWeight': 'bold',
                        'fontSize': '22px',
                        'marginBottom': '4px'
                    }),
                    html.Label(id='expense-total-display', style={
                        'fontSize': '42px'
                    })
                ], style={'textAlign': 'center', 'marginBottom': '0px'}),

                # Second row: Monthly Avg and % Change
                html.Div([
                    # Monthly Average
                    html.Div([
                        html.P("Monthly Average", style={'fontWeight': 'bold', 'minWidth': '120px', 'marginBottom': '4px'}),
                        html.Label(id='expense-avg-display', style={'fontSize': '20px'})
                    ], id='expense-avg-container', style={'textAlign': 'center'}),

                    # % Change
                    html.Div([
                        html.P(id='expense-change-title', children="% Expense Change (YTD):",
                               style={'fontWeight': 'bold', 'minWidth': '180px', 'textAlign': 'left', 'marginBottom': '4px'}),
                        html.Div([
                            html.Label(id='expense-change-display', style={'fontSize': '18px', 'minWidth': '100px'}),
                            html.Label(id='expense-change-amount', style={'fontSize': '14px', 'color': '#777', 'marginLeft': '10px'})
                        ])
                    ], style={'textAlign': 'center', 'marginLeft': '20px', 'minWidth':'100px'})
                ], style={
                    'display': 'flex',
                    'justifyContent': 'center',
                    'gap': '0px'
                })
            ], style={
                'flex': '1',
                'padding': '30px 0',
                'minWidth': '300px',
                'flexGrow': 1}
            ),

            # === Cash Section ===
            html.Div([
                # First row: Total Cash (larger font)
                html.Div([
                    html.P("Total Cash on Hand", style={
                        'fontWeight': 'bold',
                        'fontSize': '22px',
                        'marginBottom': '4px'
                    }),
                    html.Label(id='total-cash-display', style={
                        'fontSize': '42px'
                    })
                ], style={'textAlign': 'center', 'marginBottom': '0px'}),

                # Second row: % Change
                html.Div([
                    html.Div([
                        html.P(id='cash-change-title', children="% Cash Change (YTD):", style={
                            'fontWeight': 'bold', 'marginBottom': '4px'}),
                        html.Div([
                            html.Label(id='cash-change-display', style={'fontSize': '18px'}),
                            html.Label(id='cash-change-amount', style={'fontSize': '14px', 'color': '#777', 'marginLeft': '10px'})
                        ])
                    ], style={'textAlign': 'center', 'minWidth': '100px'})
                ]),
            ], style={
                'flex': '1',
                'padding': '30px 0',
                'minWidth': '300px',
                'flexGrow': 1
            }),

            # === Debt Section ===
            html.Div([
                # First row: Total Remaining Debt (larger font)
                html.Div([
                    html.P("Total Remaining Debt", style={
                        'fontWeight': 'bold',
                        'fontSize': '22px',
                        'marginBottom': '4px'
                    }),
                    html.Label(id='total-debt-display', style={
                        'fontSize': '42px'
                    })
                ], style={'textAlign': 'center', 'marginBottom': '0px'}),

                # Second row: % Change
                html.Div([
                    html.Div([
                        html.P(id='debt-change-title', children="% Debt Change (YTD):", style={
                            'fontWeight': 'bold', 'marginBottom': '4px'}),
                        html.Div([
                            html.Label(id='debt-change-display', style={'fontSize': '18px'}),
                            html.Label(id='debt-change-amount', style={'fontSize': '14px', 'color': '#777', 'marginLeft': '10px'})
                        ])
                    ], style={'textAlign': 'center', 'minWidth': '100px'})
                ])
            ], style={
                'flex': '1',
                'padding': '30px 0',
                'minWidth': '300px',
                'flexGrow': 1
            })
        ], style={
            'display': 'flex',
            'justifyContent': 'space-between',
            'alignItems': 'flex-start',
            'gap': '5px',
            'marginTop': '0px',
            'marginBottom': '40px'
        }
    ),

        # === Pie Charts (Cash on Hand & Remaining Debt) ===
        html.Div([
            html.Div(style={'width': '20px'}),
            html.Div([
                html.P("Cash Accounts",
                       style={
                            'fontWeight': 'bold',
                            'fontSize': '20px',
                            }),
                dcc.Graph(id='cash-pie-chart', config={'displayModeBar': False}, style={'height': '360px', 'minWidth': '650px'})
            ], style={'flex': '1', 'textAlign': 'center'}),
            html.Div(style={'width': '10px'}),
            html.Div([
                html.P("Debt Accounts",
                       style={
                            'fontWeight': 'bold',
                            'fontSize': '20px',
                            }),
                dcc.Graph(id='debt-pie-chart', config={'displayModeBar': False}, style={'height': '360px', 'minWidth': '650px'})
            ], style={'flex': '1', 'textAlign': 'center'})
        ], style={
            'display': 'flex',
            'justifyContent': 'center',
            'gap': '0px',
            'padding': '30px 0',
            'borderTop': '1px solid #ccc'
        })

    ]),
    html.Hr(style={
        'border': 'none',
        'borderTop': '2px solid #ccc',
        'margin': '20px 0'
    }),

    # MONTHLY BREAKDOWN SECTION
    html.Div([
        html.H2("Monthly Details", style={'textAlign': 'center', 'marginBottom': '20px'}),

        html.Div([
            # INCOME CHART + FILTER
            html.Div([
                dcc.Graph(id='monthly-income-bar-chart', style={'marginBottom': '0px', 'minWidth': '600px'}),
                html.Div([
                    html.Label("Income Source", style={
                        'fontFamily': 'Open Sans',
                        'fontSize': '16px',
                        'fontWeight': 'bold',
                        'marginBottom': '4px',
                        'marginTop': '10px',
                        'display': 'block',
                        'textAlign': 'center'
                    }),

                    # Center the checklist using a wrapper div
                    html.Div([
                        dcc.Checklist(
                            id='income-type-checklist',
                            options=[],  # dynamically filled
                            value=[],
                            inline=True,
                            style={
                                'display': 'flex',
                                'flexWrap': 'wrap',
                                'gap': '15px',
                                'fontFamily': 'Open Sans',
                                'fontSize': '16px',
                                'textAlign': 'left',
                                'marginLeft': '30px'
                            }
                        ),
                    ], style={
                        'display': 'flex',
                        'justifyContent': 'left',
                        'marginBottom': '10px',
                        'marginTop': '10px'
                    }),

                    html.Div([
                        html.Button("Select All", id="select-all-income-types", n_clicks=0),
                        html.Button("Clear All", id="clear-all-income-types", n_clicks=0),
                        dcc.Store(id='all-income-options'),
                    ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '10px', 'marginLeft': '30px', 'justifyContent': 'left'})

                ], style={'flex': '1.5', 'marginRight': '80px', 'marginLeft': '0px'}),

            ], style={'flex': '1.5', 'marginRight': '0px', 'marginLeft': '0px'}),

            # TOP 5 TRANSACTIONS TABLE
            html.Div([
                html.Div([
                    html.Label("Top Transactions", style={
                                        'font-family': 'Inter',
                                        'font-weight': '300',
                                        'letter-spacing': '0.5px',
                                        'fontSize': '18px',
                                        'marginBottom': '40px',
                                        'marginTop': '30px',
                                        'display': 'block',
                                        'textAlign': 'left'
                                    }),
                    html.Div([
                        dcc.RadioItems(
                            id='top5-toggle-mode',
                            options=[
                                {'label': 'By Amount', 'value': 'amount'},
                                {'label': 'By Frequency', 'value': 'frequency'}
                            ],
                            value='amount',  # Default selection
                            labelStyle={'display': 'inline-block', 'marginRight': '20px'},
                            style={'marginBottom': '40px', 'marginLeft': '40px', 'gap': '55px 0', 'marginTop': '30px'}
                        )
                    ])
                ], style={
                    'display': 'flex',
                    'flexWrap': 'nowrap',  # prevent vertical stacking
                    'gap': '20px',
                    'alignItems': 'flex-start',
                    'paddingTop': '0px',
                    'marginTop': '0px'
                }),

                html.Div(id='top5-purchases-table')
            ], style={
                    'flex': '1',
                    'marginRight': '0px',
                    'minWidth': '500px',
                    'flexWrap': 'nowrap',
                    'marginTop': '10px'
            })  # <-- optional margin tweak

        ], style={
            'display': 'flex',
            'flexWrap': 'nowrap',  # prevent vertical stacking
            'gap': '20px',
            'alignItems': 'flex-start',
            'paddingTop': '0px',
            'marginTop': '0px'
        }),

        html.Hr(style={
            'border': 'none',
            'borderTop': '1px solid #ccc',
            'margin': '20px 0'
        }),
        html.Div([
            html.Div([
                dcc.Graph(id='monthly-expense-bar-chart', style={'marginBottom': '0px'}),
                html.Div([
                    html.Div([
                        dcc.Input(
                            id='merchant-search',
                            type='text',
                            placeholder='Filter by merchant or transaction detail...',
                            autoComplete='off',
                            style={
                                'width': '100%',
                                'padding': '6px',
                                'fontSize': '14px',
                                'marginRight': '10px',
                                'flex': '3'
                            }
                        ),
                        html.Button('Search', id='search-button', n_clicks=0, style={
                            'padding': '4px 10px',
                            'fontSize': '13px',
                            'height': '30px',
                            'minWidth': '70px'
                        }),
                        html.Button('Clear', id='clear-button', n_clicks=0, style={
                            'padding': '4px 10px',
                            'fontSize': '13px',
                            'height': '30px',
                            'minWidth': '70px',
                            'marginLeft': '6px'
                        })
                    ], style={
                        'display': 'flex',
                        'justifyContent': 'center',
                        'gap': '6px',
                        'marginBottom': '20px',
                        'marginLeft': '60px',  # Add space on the left
                        'marginRight': '60px'  # Add space on the right
                    })

                ], style={'maxWidth': '800px', 'margin': '0 auto'}),
                dcc.Store(id='merchant-search-store'),

                # EXPENSE FILTERS
                html.Div([

                    html.Label("Expense Source", style={
                        'fontFamily': 'Open Sans',
                        'fontSize': '16px',
                        'fontWeight': 'bold',
                        'marginBottom': '0px',
                        'display': 'block',
                        'textAlign': 'center',
                        'marginRight': '150px',
                        'marginTop': '10px'
                    }),
                    html.Div("(Defaults to Top 5)",
                             style={
                                'fontFamily': 'Open Sans',
                                'fontSize': '14px',
                                'marginBottom': '0px',
                                'display': 'block',
                                'textAlign': 'center',
                                'marginRight': '150px',
                                'marginTop': '2px',
                                'fontStyle': 'italic',
                                'color': '#777'
                                }),
                    # === Debt Payments ===
                    html.Div([
                        html.P("Debt Payments", style={'fontWeight': 'bold', 'marginBottom': '6px'}),
                        dcc.Checklist(
                            id='breakdown-payments-filter',
                            options=[],
                            value=[],
                            inline=True,
                            style={
                                'display': 'flex',
                                'flexWrap': 'wrap',
                                'gap': '10px',
                                'justifyContent': 'left'
                            }
                        ),
                        html.Div([
                            html.Button("Select All", id="select-all-breakdown-payments", n_clicks=0),
                            html.Button("Clear All", id="clear-all-breakdown-payments", n_clicks=0),
                            dcc.Store(id='breakdown-payments-filter-options-store', data=sorted_payments)
                        ], style={'display': 'flex', 'gap': '10px', 'marginTop': '6px'})
                    ], style={'marginBottom': '15px'}),

                    # === General Categories ===
                    html.Div([
                        html.P("General Categories", style={'fontWeight': 'bold', 'marginBottom': '6px'}),
                        dcc.Checklist(
                            id='breakdown-expense-category-filter',
                            options=[],
                            value=[],
                            inline=True,
                            style={
                                'display': 'flex',
                                'flexWrap': 'wrap',
                                'gap': '10px',
                                'justifyContent': 'left'
                            }
                        ),
                        html.Div([
                            html.Button("Select All", id="select-all-breakdown-categories", n_clicks=0),
                            html.Button("Clear All", id="clear-all-breakdown-categories", n_clicks=0),
                            dcc.Store(id='breakdown-expense-category-filter-options-store', data=sorted_expenses)
                        ], style={'display': 'flex', 'gap': '10px', 'marginTop': '6px'})
                    ], style={'marginBottom': '15px'}),

                    # === Utilities & Insurance ===
                    html.Div([
                        html.P("Utilities & Insurance", style={'fontWeight': 'bold', 'marginBottom': '6px'}),
                        dcc.Checklist(
                            id='breakdown-utilities-insurance-filter',
                            options=[],
                            value=[],
                            inline=True,
                            style={
                                'display': 'flex',
                                'flexWrap': 'wrap',
                                'gap': '10px',
                                'justifyContent': 'left'
                            }
                        ),
                        html.Div([
                            html.Button("Select All", id="select-all-breakdown-utilities", n_clicks=0),
                            html.Button("Clear All", id="clear-all-breakdown-utilities", n_clicks=0),
                            dcc.Store(id='breakdown-utilities-insurance-filter-options-store',
                                      data=sorted_utilities_insurance)
                        ], style={'display': 'flex', 'gap': '10px', 'marginTop': '6px'})
                    ], style={'marginBottom': '15px'}),

                    # === Master Select All/Clear All ===
                    html.Div([
                        html.Button("Select All (All Categories)", id="select-all-expenses-breakdown-master", n_clicks=0),
                        html.Button("Select Top 5", id="select-top5-expenses-breakdown-master", n_clicks=0),
                        html.Button("Clear All (All Categories)", id="clear-all-expenses-breakdown-master", n_clicks=0),
                    ], style={'display': 'flex', 'gap': '10px', 'marginTop': '10px'})

                ], style={
                    'flex': '1',
                    'marginRight': '0px',
                    'minWidth': '600px',
                    'marginTop': '0px',
                    'marginBottom': '50px',
                    'marginLeft': '20px'
                })

            ]),

            html.Div([
                dcc.Graph(id='top5-expenses-pie-chart', style={
                    'flex': '1',
                    'marginRight': '0px',
                    'minWidth': '400px',
                    'marginTop': '0px',
                }),
            ])

        ], style={'display': 'flex', 'gap': '10px'}),



    ], style={'marginRight': '0px'}),
    html.Br(),
    html.Br(),
    html.Br(),
    html.Br()

], style={
    'padding': '20px 40px 20px 40px',  # Top, Right, Bottom, Left
    'maxWidth': '1200px',
    'margin': '0 auto'
})


@app.callback(
    [
        Output('selected-year-dropdown', 'options'),
        Output('selected-year-dropdown', 'value', allow_duplicate=True)
    ],
    Input('year-radio', 'value'),
    State('year-radio', 'options'),
    prevent_initial_call='initial_duplicate'
)
def populate_year_dropdown(selected_year, year_options):
    if not selected_year or not year_options:
        raise dash.exceptions.PreventUpdate

    # Reverse the year options list
    reversed_years = list(reversed(year_options))
    dropdown_options = [{'label': str(opt['label']), 'value': str(opt['value'])} for opt in reversed_years]

    return dropdown_options, str(selected_year)


@app.callback(
    [
        Output('selected-month-dropdown', 'options'),
        Output('selected-month-dropdown', 'value', allow_duplicate=True)
    ],
    Input('month-radio', 'value'),
    State('month-radio', 'options'),
    prevent_initial_call='initial_duplicate'
)
def populate_month_dropdown(selected_month, month_options):
    if selected_month is None or not month_options:
        raise dash.exceptions.PreventUpdate

    return month_options, selected_month


# This triggers a change from the year dropdown
@app.callback(
    [
        Output('year-radio', 'value', allow_duplicate=True),
        Output('month-radio', 'value', allow_duplicate=True),
        Output('year-change-store', 'data', allow_duplicate=True)
    ],
    Input('selected-year-dropdown', 'value'),
    State('month-radio', 'value'),
    prevent_initial_call=True
)
def store_year_change(selected_year, selected_month):
    if not selected_year:
        raise dash.exceptions.PreventUpdate

    selected_year = int(selected_year)
    return selected_year, selected_month, {"year": selected_year, "month": selected_month}

# This triggers a change from the month dropdown
@app.callback(
    [
        Output('year-radio', 'value', allow_duplicate=True),
        Output('month-radio', 'value', allow_duplicate=True),
        Output('year-change-store', 'data', allow_duplicate=True)
    ],
    Input('selected-month-dropdown', 'value'),
    State('year-radio', 'value'),
    prevent_initial_call=True
)
def store_month_change(selected_month, selected_year):
    if selected_month is None or selected_year is None:
        raise dash.exceptions.PreventUpdate

    return selected_year, selected_month, {"year": int(selected_year), "month": int(selected_month)}


# @app.callback(
#     [
#         Output('selected-month-dropdown', 'value'),
#         Output('selected-year-dropdown', 'value')
#     ],
#     [
#         Input('selected-month-dropdown', 'value'),
#         Input('selected-year-dropdown', 'value')
#     ]
# )
# def update_selected_month_year(month, year):
#     if not year:
#         return "", ""
#
#     month_name = "Full Year" if month == 0 else calendar.month_name[month]
#     return month_name, str(year)


@app.callback(
    [
        Output('year-radio', 'value', allow_duplicate=True),
        Output('month-radio', 'value', allow_duplicate=True),
        Output('year-change-store', 'data', allow_duplicate=True)
    ],
    Input('first-button', 'n_clicks'),
    State('year-radio', 'options'),
    prevent_initial_call=True
)
def go_to_first_year(n_clicks, year_options):
    if n_clicks:
        first_year = min([int(opt['value']) for opt in year_options])
        return first_year, 0, first_year
    raise dash.exceptions.PreventUpdate


@app.callback(
    [Output('year-radio', 'value', allow_duplicate=True),
     Output('month-radio', 'value', allow_duplicate=True),
     Output('prev-year-button', 'disabled'),
     Output('year-change-store', 'data', allow_duplicate=True)],
    Input('prev-year-button', 'n_clicks'),
    [State('year-radio', 'value'),
     State('month-radio', 'value'),
     State('year-radio', 'options')],
    prevent_initial_call='initial_duplicate'
)
def go_to_previous_year(n_clicks, current_year, current_month, year_options):
    if not n_clicks or not current_year or not year_options:
        raise dash.exceptions.PreventUpdate

    current_year = int(current_year)
    sorted_years = sorted([int(opt['value']) for opt in year_options])
    first_year = sorted_years[0]

    # Case 1: Currently on a month view — go to full year of the *same* year
    if current_month != 0:
        disable_button = current_year == first_year
        return current_year, 0, disable_button, current_year

    # Case 2: Already at first year and full year view
    if current_year == first_year and current_month == 0:
        return dash.no_update, dash.no_update, True, dash.no_update

    # Case 3: Go to full year of previous year
    prev_year = current_year - 1
    disable_button = prev_year == first_year
    return prev_year, 0, disable_button, prev_year



@app.callback(
    [Output('year-radio', 'value', allow_duplicate=True),
     Output('month-radio', 'value', allow_duplicate=True),
     Output('year-change-store', 'data', allow_duplicate=True)],
    Input('prev-month-button', 'n_clicks'),
    [State('year-radio', 'value'),
     State('month-radio', 'value'),
     State('year-radio', 'options')],
    prevent_initial_call=True
)
def go_to_previous_month(n_clicks, current_year, current_month, year_options):
    if not current_year or not year_options:
        raise dash.exceptions.PreventUpdate

    current_year = int(current_year)
    sorted_years = sorted([int(opt['value']) for opt in year_options])
    first_year = sorted_years[0]

    if current_month == 0:
        # From Full Year → Go to December of previous year (if available)
        if current_year == first_year:
            raise dash.exceptions.PreventUpdate  # Already at first available year
        return current_year - 1, 12, current_year - 1

    elif current_month == 1:
        # From January → Go to Full Year of same year
        return current_year, 0, current_year


    else:
        # Standard decrement
        return current_year, current_month - 1, current_year

@app.callback(
    [
        Output('year-radio', 'value', allow_duplicate=True),
        Output('month-radio', 'value', allow_duplicate=True),
        Output('year-change-store', 'data', allow_duplicate=True)
    ],
    Input('next-month-button', 'n_clicks'),
    [
        State('year-radio', 'value'),
        State('month-radio', 'value'),
        State('year-radio', 'options')
    ],
    prevent_initial_call=True
)
def go_to_next_month(n_clicks, current_year, current_month, year_options):
    if not n_clicks or not current_year or not year_options:
        raise dash.exceptions.PreventUpdate

    current_year = int(current_year)
    sorted_years = sorted([int(opt['value']) for opt in year_options])
    latest_year = sorted_years[-1]

    if current_month == 0:
        # Full Year → go to January of same year
        return current_year, 1, current_year

    elif current_month == 12:
        # December → go to Full Year of next year if possible
        if current_year < latest_year:
            return current_year + 1, 0, current_year + 1
        else:
            raise dash.exceptions.PreventUpdate

    else:
        # Any other month → go to next month
        return current_year, current_month + 1, current_year

@app.callback(
    [
        Output('year-radio', 'value', allow_duplicate=True),
        Output('month-radio', 'value', allow_duplicate=True),
        Output('next-year-button', 'disabled', allow_duplicate=True),
        Output('year-change-store', 'data', allow_duplicate=True)
    ],
    Input('next-year-button', 'n_clicks'),
    [
        State('year-radio', 'value'),
        State('month-radio', 'value'),
        State('year-radio', 'options')
    ],
    prevent_initial_call=True
)
def go_to_next_year(n_clicks, current_year, current_month, year_options):
    if not n_clicks or not current_year or not year_options:
        raise dash.exceptions.PreventUpdate

    current_year = int(current_year)
    sorted_years = sorted([int(opt['value']) for opt in year_options])
    latest_year = sorted_years[-1]

    if current_year == latest_year:
        # Already at the latest year
        return dash.no_update, dash.no_update, True, dash.no_update

    next_year = current_year + 1
    disable_button = next_year == latest_year

    # Regardless of current month, go to Full Year of next year
    return next_year, 0, disable_button, next_year


@app.callback(
    [Output('year-radio', 'value', allow_duplicate=True),
     Output('month-radio', 'value', allow_duplicate=True),
     Output('next-year-button', 'disabled', allow_duplicate=True),
     Output('first-button', 'disabled'),
     Output('year-change-store', 'data', allow_duplicate=True)],
    Input('latest-button', 'n_clicks'),
    State('year-radio', 'options'),
    prevent_initial_call=True
)
def go_to_latest_year(n_clicks, year_options):
    if not n_clicks or not year_options:
        raise dash.exceptions.PreventUpdate

    sorted_years = sorted([int(opt['value']) for opt in year_options])
    latest_year = sorted_years[-1]

    return latest_year, 0, True, False, latest_year



@app.callback(
    Output('first-button', 'disabled', allow_duplicate=True),
    Input('year-radio', 'value'),
    State('year-radio', 'options'),
    prevent_initial_call='initial_duplicate'
)
def toggle_first_button(current_year, year_options):
    if not current_year or not year_options:
        return True

    sorted_years = sorted([int(opt['value']) for opt in year_options])
    return int(current_year) == sorted_years[0]


@app.callback(
    Output('prev-year-button', 'disabled', allow_duplicate=True),
    [Input('year-radio', 'value')],
    [State('month-radio', 'value'),
     State('year-radio', 'options')],
    prevent_initial_call='initial_duplicate'
)
def toggle_prev_year_button(current_year, current_month, year_options):
    if not current_year or not year_options:
        return True

    current_year = int(current_year)
    current_month = int(current_month)
    sorted_years = sorted([int(opt['value']) for opt in year_options])
    first_year = sorted_years[0]

    # Disable only if you're on Full Year view of the first year
    if current_year == first_year and current_month == 0:
        return True
    return False



@app.callback(
    Output('prev-month-button', 'disabled', allow_duplicate=True),
    [Input('month-radio', 'value'),
     Input('year-radio', 'value')],
    State('year-radio', 'options'),
    prevent_initial_call='initial_duplicate'
)
def toggle_prev_month_button(current_month, current_year, year_options):
    if current_year is None or current_month is None or not year_options:
        return True

    sorted_years = sorted([int(opt['value']) for opt in year_options])
    is_first_year = int(current_year) == sorted_years[0]
    is_first_month_or_full = current_month in [0]  # Full Year

    return is_first_year and is_first_month_or_full

@app.callback(
    Output('next-month-button', 'disabled', allow_duplicate=True),
    [
        Input('year-radio', 'value'),
        Input('month-radio', 'value')
    ],
    State('year-radio', 'options'),
    prevent_initial_call='initial_duplicate'
)
def toggle_next_month_button(current_year, current_month, year_options):
    if not current_year or current_month is None:
        return True

    sorted_years = sorted([int(opt['value']) for opt in year_options])
    latest_year = sorted_years[-1]

    latest_month_by_year = (
        df.groupby(df['Date'].dt.year)['Date']
        .max()
        .dt.month
        .to_dict()
    )

    if int(current_year) == latest_year:
        latest_month = latest_month_by_year.get(str(latest_year), 12)
        return current_month >= latest_month

    return False

@app.callback(
    Output('next-year-button', 'disabled', allow_duplicate=True),
    Input('year-radio', 'value'),
    State('year-radio', 'options'),
    prevent_initial_call='initial_duplicate'
)
def toggle_next_year_button(current_year, year_options):
    if not current_year or not year_options:
        return True

    sorted_years = sorted([int(opt['value']) for opt in year_options])
    return int(current_year) == sorted_years[-1]


@app.callback(
    Output('latest-button', 'disabled', allow_duplicate=True),
    Input('year-radio', 'value'),
    State('year-radio', 'options'),
    prevent_initial_call='initial_duplicate'
)
def toggle_latest_year_button(current_year, year_options):
    if not current_year or not year_options:
        return True

    sorted_years = sorted([int(opt['value']) for opt in year_options])
    return int(current_year) == sorted_years[-1]


@app.callback(
    Output('income-to-expense-gauge', 'figure'),
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_income_to_expense_gauge(selected_year, selected_month):
    selected_year = int(selected_year)

    income = income_data[income_data['Date'].dt.year == selected_year]
    expense = all_expense_data[all_expense_data['Date'].dt.year == selected_year]

    if income.empty or expense.empty:
        return go.Figure()

    # Determine current and previous month to compare
    if selected_month == 0:  # Full year
        latest_month = min(income['Date'].dt.month.max(), expense['Date'].dt.month.max())
        income_total = income[income['Date'].dt.month <= latest_month]['Amount'].sum()
        expense_total = expense[expense['Date'].dt.month <= latest_month]['Amount'].sum()
    else:
        income_total = income[income['Date'].dt.month == selected_month]['Amount'].sum()
        expense_total = expense[expense['Date'].dt.month == selected_month]['Amount'].sum()

    # Avoid divide-by-zero
    if expense_total == 0:
        value = 2
    else:
        value = income_total / expense_total

    # Determine label and color
    if value >= 1.5:
        label = "Excellent – Strong Savings"
        bar_color = "green"
    elif value >= 1.2:
        label = "Good – Healthy Buffer"
        bar_color = "yellowgreen"
    elif value >= 1.0:
        label = "Moderate – Breaking Even"
        bar_color = "orange"
    else:
        label = "Risky – Spending Too Much"
        bar_color = "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'valueformat': '.2f'},
        gauge={
            'axis': {
                'range': [0, 2],
                'tickvals': [0, 1.0, 1.2, 1.5, 2.0],
                'ticktext': ['0', '1.0', '1.2', '1.5', '2.0'],
                'tickwidth': 1,
                'tickcolor': "darkgray"
            },
            'bar': {'color': bar_color},
            'steps': [
                {'range': [0, 1.0], 'color': '#ffcccc'},     # Risky
                {'range': [1.0, 1.2], 'color': '#ffe0b3'},   # Moderate
                {'range': [1.2, 1.5], 'color': '#e6f5cc'},   # Good
                {'range': [1.5, 2.0], 'color': '#d6f5d6'}    # Excellent
            ],
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.75,
                'value': 1.2
            }
        },
        domain={'x': [0, 1], 'y': [0.3, 1]}
    ))

    # Add title and subtitle
    fig.add_annotation(
        text="Income-to-Expense Ratio",
        showarrow=False,
        x=0.5,
        y=0.18,
        font=dict(size=16)
    )

    fig.add_annotation(
        text=label,
        showarrow=False,
        x=0.5,
        y=0.08,
        font=dict(size=13, color=bar_color)
    )

    fig.update_layout(margin=dict(t=20, b=0, l=0, r=0), height=220)

    return fig

# @app.callback(
#     Output('month-radio', 'value'),
#     Input('year-radio', 'value')
# )
# def reset_month_on_year_change(selected_year):
#     return 0  # Default to 'Full Year'

@app.callback(
    Output('cash-to-debt-gauge', 'figure'),
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_cash_to_debt_gauge(selected_year, selected_month):
    selected_year = int(selected_year)

    # Filter cash and debt data for selected year
    cash = df[(df['Category'] == 'CASH_ON_HAND') & (df['Date'].dt.year == selected_year)]
    debt = debt_data[debt_data['Date'].dt.year == selected_year]

    if cash.empty or debt.empty:
        return go.Figure()

    if selected_month == 0:
        latest_month = min(cash['Date'].dt.month.max(), debt['Date'].dt.month.max())
    else:
        latest_month = selected_month

    # Filter for the most recent snapshot
    current_cash = cash[cash['Date'].dt.month == latest_month]['Amount'].sum()
    current_debt = abs(debt[debt['Date'].dt.month == latest_month]['Amount'].sum())

    if current_debt == 0:
        value = 2  # Cap at upper range
    else:
        value = current_cash / current_debt

    # Determine label and color
    if value >= 1.0:
        label = "Excellent – Strong Flexibility"
        bar_color = "green"
    elif value >= 0.5:
        label = "Good – Covers Half or More"
        bar_color = "yellowgreen"
    elif value >= 0.2:
        label = "Caution – Limited Reserves"
        bar_color = "darkorange"
    else:
        label = "Risky – Low Liquidity"
        bar_color = "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'valueformat': '.2f'},
        gauge={
            'axis': {
                'range': [0, 2],
                'tickvals': [0, 0.2, 0.5, 1.0, 2.0],
                'ticktext': ['0', '0.2', '0.5', '1.0', '2.0'],
                'tickwidth': 1,
                'tickcolor': "darkgray"
            },
            'bar': {'color': bar_color},
            'steps': [
                {'range': [0, 0.2], 'color': '#ffdddd'},
                {'range': [0.2, 0.5], 'color': '#ffebb3'},
                {'range': [0.5, 1.0], 'color': '#e6f5cc'},
                {'range': [1.0, 2.0], 'color': '#d6f5d6'}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.75,
                'value': 0.5
            }
        },
        domain={'x': [0, 1], 'y': [0.3, 1]}
    ))

    fig.add_annotation(
        text="Cash-to-Debt Ratio",
        showarrow=False,
        x=0.5,
        y=0.18,
        font=dict(size=16)
    )

    fig.add_annotation(
        text=label,
        showarrow=False,
        x=0.5,
        y=0.08,
        font=dict(size=13, color=bar_color)
    )

    fig.update_layout(margin=dict(t=20, b=0, l=0, r=0), height=220)

    return fig

@app.callback(
    Output('debt-to-income-gauge', 'figure'),
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_debt_to_income_gauge(selected_year, selected_month):
    selected_year = int(selected_year)

    income = income_data[income_data['Date'].dt.year == selected_year]
    payments = payment_data[payment_data['Date'].dt.year == selected_year]

    if selected_month != 0:
        income = income[income['Date'].dt.month == selected_month]
        payments = payments[payments['Date'].dt.month == selected_month]

    monthly_income = income['Amount'].sum()
    monthly_payments = payments['Amount'].sum()

    if monthly_income == 0:
        value = 1
    else:
        value = monthly_payments / monthly_income

    # Determine label and color
    if value <= 0.2:
        label = "Excellent – Low Debt Burden"
        bar_color = "green"
    elif value <= 0.36:
        label = "Good – Manageable"
        bar_color = "yellowgreen"
    elif value <= 0.43:
        label = "Caution – Getting High"
        bar_color = "orange"
    else:
        label = "Risky – Debt Too High"
        bar_color = "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'valueformat': '.2f'},
        gauge={
            'axis': {
                'range': [1.0, 0],  # Reversed range
                'tickvals': [1.0, 0.43, 0.36, 0.2, 0],
                'ticktext': ['1.0', '0.43', '0.36', '0.2', '0'],
                'tickwidth': 1,
                'tickcolor': "darkgray"
            },
            'bar': {'color': bar_color},
            'steps': [
                {'range': [1.0, 0.43], 'color': '#ffcccc'},  # Risky
                {'range': [0.43, 0.36], 'color': '#ffe0b3'},  # Caution
                {'range': [0.36, 0.2], 'color': '#e6ffcc'},  # Good
                {'range': [0.2, 0], 'color': '#d6f5d6'}  # Excellent
            ],
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.75,
                'value': 0.36
            }
        },
        domain={'x': [0, 1], 'y': [0.3, 1]}
    ))

    fig.add_annotation(
        text="Debt-Payments-to-Income Ratio",
        showarrow=False,
        x=0.5,
        y=0.18,
        font=dict(size=16)
    )

    fig.add_annotation(
        text=label,
        showarrow=False,
        x=0.5,
        y=0.08,
        font=dict(size=13, color=bar_color)
    )

    fig.update_layout(margin=dict(t=20, b=0, l=0, r=0), height=220)

    return fig



@app.callback(
    [Output('income-change-title', 'children'),
     Output('expense-change-title', 'children'),
     Output('debt-change-title', 'children'),
     Output('cash-change-title', 'children')],
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_change_titles(selected_year, selected_month):
    selected_year = int(selected_year)

    if selected_month == 0:  # Full Year
        latest_year = df['Date'].dt.year.max()
        if selected_year == latest_year:
            title_suffix = "(YTD)"
        else:
            title_suffix = "(Last Year)"
    else:
        title_suffix = "(Last Month)"

    return (
        f"% Change {title_suffix}:",
        f"% Change {title_suffix}:",
        f"% Change {title_suffix}:",
        f"% Change {title_suffix}:"
    )

@app.callback(
    [Output('income-avg-container', 'style'),
     Output('expense-avg-container', 'style')],
    Input('month-radio', 'value')
)
def toggle_income_avg_visibility(selected_month):
    if selected_month == 0:  # Full Year
        return {'textAlign': 'center'}, {'textAlign': 'center'}
    else:
        return {'display': 'none'}, {'display': 'none'}



@app.callback(
    [Output('income-total-display', 'children'),
     Output('income-avg-display', 'children'),
     Output('income-change-display', 'children'),
     Output('income-change-amount', 'children')],
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_income_overview(selected_year, selected_month):
    selected_year = int(selected_year)

    if selected_month == 0:
        # Full Year (YTD) logic
        income_current = income_data[income_data['Date'].dt.year == selected_year]
        if income_current.empty:
            return "No data", "", "N/A", html.Span("", style={'color': '#777'})

        latest_month = income_current['Date'].dt.month.max()
        months_available = latest_month if selected_year == df['Date'].dt.year.max() else 12

        ytd_income_total = income_current[income_current['Date'].dt.month <= latest_month]['Amount'].sum()
        monthly_avg = ytd_income_total / months_available

        # Compare to previous year
        income_prev = income_data[income_data['Date'].dt.year == selected_year - 1]
        if not income_prev.empty:
            prev_income_total = income_prev[income_prev['Date'].dt.month <= latest_month]['Amount'].sum()
            change_amount = ytd_income_total - prev_income_total
            change_percent = f"{(change_amount / prev_income_total) * 100:+.2f}%"
            change_dollars = f"${change_amount:+,.0f}"
            change_color = 'green' if change_amount > 0 else 'red'
        else:
            change_percent = "N/A"
            change_dollars = ""
            change_color = '#777'

        return (
            f"${ytd_income_total:,.0f}",
            f"${monthly_avg:,.0f}",
            change_percent,
            html.Span(change_dollars, style={'color': change_color})
        )

    else:
        # Single month logic
        income_current = income_data[
            (income_data['Date'].dt.year == selected_year) &
            (income_data['Date'].dt.month == selected_month)
        ]

        if selected_month == 1:
            # Compare January to December of previous year
            income_prev = income_data[
                (income_data['Date'].dt.year == selected_year - 1) &
                (income_data['Date'].dt.month == 12)
            ]
        else:
            # Compare to previous month of same year
            income_prev = income_data[
                (income_data['Date'].dt.year == selected_year) &
                (income_data['Date'].dt.month == selected_month - 1)
            ]

        ytd_income_total = income_current['Amount'].sum()
        prev_total = income_prev['Amount'].sum()
        monthly_avg = ytd_income_total  # Single month average is the total

        if prev_total > 0:
            change_amount = ytd_income_total - prev_total
            change_percent = f"{(change_amount / prev_total) * 100:+.2f}%"
            change_dollars = f"${change_amount:+,.0f}"
            change_color = 'green' if change_amount > 0 else 'red'
        else:
            change_percent = "N/A"
            change_dollars = ""
            change_color = '#777'

        return (
            f"${ytd_income_total:,.0f}",
            f"${monthly_avg:,.0f}",
            change_percent,
            html.Span(change_dollars, style={'color': change_color})
        )


@app.callback(
    [Output('expense-total-display', 'children'),
     Output('expense-avg-display', 'children'),
     Output('expense-change-display', 'children'),
     Output('expense-change-amount', 'children')],
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_expense_overview(selected_year, selected_month):
    selected_year = int(selected_year)


    if selected_month == 0:
        # Full Year (YTD) logic
        expense_current = all_expense_data[all_expense_data['Date'].dt.year == selected_year]
        if expense_current.empty:
            return "No data", "", "N/A", html.Span("", style={'color': '#777'})

        latest_month = expense_current['Date'].dt.month.max()
        months_available = latest_month if selected_year == df['Date'].dt.year.max() else 12

        ytd_expense_total = expense_current[expense_current['Date'].dt.month <= latest_month]['Amount'].sum()
        monthly_avg = ytd_expense_total / months_available

        # Compare to previous year
        expense_prev = all_expense_data[all_expense_data['Date'].dt.year == selected_year - 1]
        if not expense_prev.empty:
            prev_expense_total = expense_prev[expense_prev['Date'].dt.month <= latest_month]['Amount'].sum()
            change_amount = ytd_expense_total - prev_expense_total
            change_percent = f"{(change_amount / prev_expense_total) * 100:+.2f}%"
            change_dollars = f"${change_amount:+,.0f}"
            change_color = 'green' if change_amount < 0 else 'red'
        else:
            change_percent = "N/A"
            change_dollars = ""
            change_color = '#777'

        return (
            f"${abs(ytd_expense_total):,.0f}",
            f"${abs(monthly_avg):,.0f}",
            change_percent,
            html.Span(change_dollars, style={'color': change_color})
        )

    else:
        # Single month logic
        expense_current = all_expense_data[
            (all_expense_data['Date'].dt.year == selected_year) &
            (all_expense_data['Date'].dt.month == selected_month)
            ]

        if selected_month == 1:
            # Compare January to December of previous year
            expense_prev = all_expense_data[
                (all_expense_data['Date'].dt.year == selected_year - 1) &
                (all_expense_data['Date'].dt.month == 12)
                ]
        else:
            # Compare to previous month of same year
            expense_prev = all_expense_data[
                (all_expense_data['Date'].dt.year == selected_year) &
                (all_expense_data['Date'].dt.month == selected_month - 1)
                ]

        ytd_expense_total = expense_current['Amount'].sum()
        prev_total = expense_prev['Amount'].sum()
        monthly_avg = ytd_expense_total  # For single month view

        if prev_total > 0:
            change_amount = ytd_expense_total - prev_total
            change_percent = f"{(change_amount / prev_total) * 100:+.2f}%"
            change_dollars = f"${change_amount:+,.0f}"
            change_color = 'green' if change_amount < 0 else 'red'
        else:
            change_percent = "N/A"
            change_dollars = ""
            change_color = '#777'

        return (
            f"${abs(ytd_expense_total):,.0f}",
            f"${abs(monthly_avg):,.0f}",
            change_percent,
            html.Span(change_dollars, style={'color': change_color})
        )


@app.callback(
    Output('income-expense-ratio', 'children'),
    Input('year-radio', 'value')
)
def update_income_expense_ratio(selected_year):
    selected_year = int(selected_year)

    income = income_data[income_data['Date'].dt.year == selected_year]
    expense = all_expense_data[all_expense_data['Date'].dt.year == selected_year]

    if income.empty or expense.empty:
        return html.Span("N/A", style={'color': '#777'})

    latest_month = max(income['Date'].dt.month.max(), expense['Date'].dt.month.max())

    ytd_income = income[income['Date'].dt.month <= latest_month]['Amount'].sum()
    ytd_expense = expense[expense['Date'].dt.month <= latest_month]['Amount'].sum()

    if ytd_expense == 0:
        return html.Span("∞", style={'color': 'green'})

    ratio = ytd_income / ytd_expense
    color = 'green' if ratio >= 1 else 'red'

    return html.Span(f"{ratio:.2f}", style={'color': color})

@app.callback(
    Output('cash-to-debt-ratio', 'children'),
    Input('year-radio', 'value')
)
def update_cash_to_debt_ratio(selected_year):
    selected_year = int(selected_year)

    # Get cash and debt snapshots for the selected year
    cash_snapshot = df[
        (df['Category'] == 'CASH_ON_HAND') &
        (df['Date'].dt.year == selected_year)
    ]
    debt_snapshot = debt_data[
        debt_data['Date'].dt.year == selected_year
    ]

    if cash_snapshot.empty or debt_snapshot.empty:
        return html.Span("N/A", style={'color': '#777'})

    # Get latest month snapshot
    latest_month = cash_snapshot['Date'].dt.month.max()
    current_cash = cash_snapshot[cash_snapshot['Date'].dt.month == latest_month]['Amount'].sum()
    current_debt = debt_snapshot[debt_snapshot['Date'].dt.month == latest_month]['Amount'].sum()

    if current_debt == 0:
        return html.Span("∞", style={'color': 'green'})

    ratio = current_cash / current_debt
    ratio_str = f"{ratio:.2f}"
    color = 'green' if ratio >= 1 else 'red'

    return html.Span(ratio_str, style={'color': color})

@app.callback(
    [Output('total-debt-display', 'children'),
     Output('debt-change-display', 'children'),
     Output('debt-change-amount', 'children'),
     Output('debt-pie-chart', 'figure')],
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_debt_overview(selected_year, selected_month):
    selected_year = int(selected_year)

    if selected_month == 0:
        # Full Year (YTD) logic
        current_year_debt = debt_data[debt_data['Date'].dt.year == selected_year]
        if current_year_debt.empty:
            return "No data", "N/A", "", go.Figure()

        latest_month = current_year_debt['Date'].dt.month.max()
        current_snapshot = current_year_debt[current_year_debt['Date'].dt.month == latest_month]
        total_debt = current_snapshot['Amount'].sum()

        prev_year_debt = debt_data[
            (debt_data['Date'].dt.year == selected_year - 1) &
            (debt_data['Date'].dt.month == latest_month)
        ]

    else:
        # Single month logic
        current_snapshot = debt_data[
            (debt_data['Date'].dt.year == selected_year) &
            (debt_data['Date'].dt.month == selected_month)
        ]
        total_debt = current_snapshot['Amount'].sum()

        if selected_month == 1:
            prev_year_debt = debt_data[
                (debt_data['Date'].dt.year == selected_year - 1) &
                (debt_data['Date'].dt.month == 12)
            ]
        else:
            prev_year_debt = debt_data[
                (debt_data['Date'].dt.year == selected_year) &
                (debt_data['Date'].dt.month == selected_month - 1)
            ]

    if not prev_year_debt.empty:
        prev_total = prev_year_debt['Amount'].sum()
        change_amount = total_debt - prev_total
        change_percent = f"{(change_amount / prev_total) * 100:+.2f}%"
        change_dollars = f"${change_amount:+,.0f}"
        change_color = 'green' if change_amount < 0 else 'red'
    else:
        change_percent = "N/A"
        change_dollars = ""
        change_color = '#777'

    labels = current_snapshot[current_snapshot['Amount'] > 0]['Sub-Category (Account)']
    values = current_snapshot[current_snapshot['Amount'] > 0]['Amount']
    colors = [debt_colors.get(label, '#888') for label in labels]

    pie_fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            textinfo='label+percent',
            hovertemplate='%{label}<br>$%{value:,.2f}<extra></extra>',
            marker=dict(colors=colors)
        )
    ])

    pie_fig.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0))

    return (
        f"${abs(total_debt):,.0f}",
        change_percent,
        html.Span(f"{change_dollars}", style={'color': change_color}),
        pie_fig
    )


@app.callback(
    [Output('total-cash-display', 'children'),
     Output('cash-change-display', 'children'),
     Output('cash-change-amount', 'children'),
     Output('cash-pie-chart', 'figure')],
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_cash_overview(selected_year, selected_month):
    selected_year = int(selected_year)

    if selected_month == 0:
        # YTD logic
        current_cash = df[
            (df['Category'] == 'CASH_ON_HAND') &
            (df['Date'].dt.year == selected_year)
        ]
        if current_cash.empty:
            return "No data", "N/A", "", go.Figure()

        latest_month = current_cash['Date'].dt.month.max()
        current_snapshot = current_cash[current_cash['Date'].dt.month == latest_month]
        total_cash = current_snapshot['Amount'].sum()

        prev_cash = df[
            (df['Category'] == 'CASH_ON_HAND') &
            (df['Date'].dt.year == selected_year - 1)
        ]
        if not prev_cash.empty:
            latest_prev_month = prev_cash['Date'].dt.month.max()
            prev_snapshot = prev_cash[prev_cash['Date'].dt.month == latest_prev_month]
            prev_total = prev_snapshot['Amount'].sum()

            change_amount = total_cash - prev_total
            change_percent = f"{(change_amount / prev_total) * 100:+.2f}%"
            change_dollars = f"{change_amount:+,.0f}"
            change_color = 'green' if change_amount > 0 else 'red'
        else:
            change_percent = "N/A"
            change_dollars = ""
            change_color = '#777'

    else:
        # Single month logic
        current_snapshot = df[
            (df['Category'] == 'CASH_ON_HAND') &
            (df['Date'].dt.year == selected_year) &
            (df['Date'].dt.month == selected_month)
        ]
        total_cash = current_snapshot['Amount'].sum()

        if selected_month == 1:
            prev_snapshot = df[
                (df['Category'] == 'CASH_ON_HAND') &
                (df['Date'].dt.year == selected_year - 1) &
                (df['Date'].dt.month == 12)
            ]
        else:
            prev_snapshot = df[
                (df['Category'] == 'CASH_ON_HAND') &
                (df['Date'].dt.year == selected_year) &
                (df['Date'].dt.month == selected_month - 1)
            ]

        prev_total = prev_snapshot['Amount'].sum()

        if prev_total > 0:
            change_amount = total_cash - prev_total
            change_percent = f"{(change_amount / prev_total) * 100:+.2f}%"
            change_dollars = f"{change_amount:+,.0f}"
            change_color = 'green' if change_amount > 0 else 'red'
        else:
            change_percent = "N/A"
            change_dollars = ""
            change_color = '#777'

    # Pie chart for current snapshot
    labels = current_snapshot[current_snapshot['Amount'] > 0]['Sub-Category (Account)']
    values = current_snapshot[current_snapshot['Amount'] > 0]['Amount']
    colors = [cash_colors.get(label, '#888') for label in labels]

    pie_fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            textinfo='label+percent',
            hovertemplate='%{label}<br>$%{value:,.2f}<extra></extra>',
            marker=dict(colors=colors)
        )
    ])
    pie_fig.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0))

    return (
        f"${total_cash:,.0f}",
        change_percent,
        html.Span(f"${change_dollars}", style={'color': change_color}),
        pie_fig
    )



@app.callback(
    Output('yearly-summary-title', 'children'),
    Input('year-radio', 'value')
)
def update_summary_title(selected_year):
    return html.Div([
        html.H1("Yearly Summary", style={'marginBottom': '6px'}),
    ])


# Callback to render the correct layout based on the URL path
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/income-expense':
        return income_vs_expenses_layout
    elif pathname == '/' or pathname == '/yearly-summary':
        return yearly_summary_layout
    else:
        return html.Div("404 - Page not found", style={'textAlign': 'center', 'padding': '50px'})



@app.callback(
    [Output('income-type-checklist', 'options'),
     Output('income-type-checklist', 'value'),
     Output('all-income-options', 'data')],
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_income_type_options(selected_year, selected_month):
    # Filter income data by selected year
    filtered_income = income_data[income_data['Date'].dt.year == selected_year]

    # If a specific month is selected, filter further
    if selected_month != 0:
        filtered_income = filtered_income[filtered_income['Date'].dt.month == selected_month]

    if filtered_income.empty:
        return [], [], []

    # Group by income source and sort by total amount (descending)
    totals = (
        filtered_income
        .groupby('Sub-Category (Account)')['Amount']
        .sum()
        .sort_values(ascending=False)
    )

    # Build checklist options
    options = [{'label': i, 'value': i} for i in totals.index]
    sorted_values = list(totals.index)

    return options, sorted_values, sorted_values



@app.callback(
    Output('income-type-checklist', 'value', allow_duplicate=True),
    [Input('select-all-income-types', 'n_clicks'),
     Input('clear-all-income-types', 'n_clicks')],
    State('all-income-options', 'data'),
    prevent_initial_call=True
)
def toggle_income_type_selection(n_select, n_clear, all_options):
    ctx = dash.callback_context
    if not ctx.triggered or all_options is None:
        return dash.no_update

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'select-all-income-types':
        return all_options
    elif button_id == 'clear-all-income-types':
        return []
    return dash.no_update


# Individual section select/clear
@app.callback(
    Output('breakdown-payments-filter', 'value', allow_duplicate=True),
    [Input('select-all-breakdown-payments', 'n_clicks'),
     Input('clear-all-breakdown-payments', 'n_clicks')],
    State('breakdown-payments-filter-options-store', 'data'),
    prevent_initial_call=True
)
def toggle_breakdown_payments(select_all, clear_all, options):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    return options if ctx.triggered_id == 'select-all-breakdown-payments' else []

@app.callback(
    Output('breakdown-utilities-insurance-filter', 'value', allow_duplicate=True),
    [Input('select-all-breakdown-utilities', 'n_clicks'),
     Input('clear-all-breakdown-utilities', 'n_clicks')],
    State('breakdown-utilities-insurance-filter-options-store', 'data'),
    prevent_initial_call=True
)
def toggle_breakdown_utilities(select_all, clear_all, options):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    return options if ctx.triggered_id == 'select-all-breakdown-utilities' else []

@app.callback(
    Output('breakdown-expense-category-filter', 'value', allow_duplicate=True),
    [Input('select-all-breakdown-categories', 'n_clicks'),
     Input('clear-all-breakdown-categories', 'n_clicks')],
    State('breakdown-expense-category-filter-options-store', 'data'),
    prevent_initial_call=True
)
def toggle_breakdown_categories(select_all, clear_all, options):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    return options if ctx.triggered_id == 'select-all-breakdown-categories' else []


@app.callback(
    [Output('breakdown-payments-filter', 'options'),
     Output('breakdown-payments-filter-options-store', 'data'),
     Output('breakdown-utilities-insurance-filter', 'options'),
     Output('breakdown-utilities-insurance-filter-options-store', 'data'),
     Output('breakdown-expense-category-filter', 'options'),
     Output('breakdown-expense-category-filter-options-store', 'data')],
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_all_expense_breakdown_filters(year, month):
    # === Payments ===
    payments_filtered = payment_data[payment_data['Date'].dt.year == year]
    if month != 0:
        payments_filtered = payments_filtered[payments_filtered['Date'].dt.month == month]

    sorted_payments = (
        payments_filtered.groupby('Sub-Category (Account)')['Amount']
        .sum().sort_values(ascending=False).index.tolist()
    )
    payments_options = [{'label': cat, 'value': cat} for cat in sorted_payments]

    # === Utilities & Insurance ===
    ui_filtered = pd.concat([utilities_data, insurance_data])
    ui_filtered = ui_filtered[ui_filtered['Date'].dt.year == year]
    if month != 0:
        ui_filtered = ui_filtered[ui_filtered['Date'].dt.month == month]

    sorted_ui = (
        ui_filtered.groupby('Sub-Category (Account)')['Amount']
        .sum().sort_values(ascending=False).index.tolist()
    )
    ui_options = [{'label': cat, 'value': cat} for cat in sorted_ui]

    # === General Expense Categories ===
    general_filtered = expenses_data[expenses_data['Date'].dt.year == year]
    if month != 0:
        general_filtered = general_filtered[general_filtered['Date'].dt.month == month]

    sorted_expenses = (
        general_filtered.groupby('Sub-Category (Account)')['Amount']
        .sum().sort_values(ascending=False).index.tolist()
    )
    expense_options = [{'label': cat, 'value': cat} for cat in sorted_expenses]

    return (
        payments_options, sorted_payments,
        ui_options, sorted_ui,
        expense_options, sorted_expenses
    )



@app.callback(
    [
        Output('breakdown-payments-filter', 'value'),
        Output('breakdown-utilities-insurance-filter', 'value'),
        Output('breakdown-expense-category-filter', 'value'),
    ],
    [
        Input('year-radio', 'value'),
        Input('month-radio', 'value'),
    ],
    State('merchant-search-store', 'data'),
    prevent_initial_call=True
)
def auto_select_top5_breakdown_expenses (year, month, stored_search_value):
    # === Filter the full dataset by year/month ===
    data = all_expense_data[all_expense_data['Date'].dt.year == year]
    if month != 0:
        data = data[data['Date'].dt.month == month]

    # Optional search filter
    if stored_search_value:
        search_term = stored_search_value.lower().strip()
        data = data[data['Description (Transaction Detail)'].str.lower().str.contains(search_term)]

    if data.empty:
        return [], [], []

    # Payments
    filtered_payments = payment_data[payment_data['Date'].dt.year == year]
    if month != 0:
        filtered_payments = filtered_payments[filtered_payments['Date'].dt.month == month]
    current_payment_categories = filtered_payments['Sub-Category (Account)'].unique().tolist()

    # Utilities & Insurance
    filtered_ui = pd.concat([utilities_data, insurance_data])
    filtered_ui = filtered_ui[filtered_ui['Date'].dt.year == year]
    if month != 0:
        filtered_ui = filtered_ui[filtered_ui['Date'].dt.month == month]
    current_ui_categories = filtered_ui['Sub-Category (Account)'].unique().tolist()

    # General Expenses
    filtered_expenses = expenses_data[expenses_data['Date'].dt.year == year]
    if month != 0:
        filtered_expenses = filtered_expenses[filtered_expenses['Date'].dt.month == month]
    current_expense_categories = filtered_expenses['Sub-Category (Account)'].unique().tolist()

    # Top 5 across all categories
    top5_cats = (
        data.groupby('Sub-Category (Account)')['Amount']
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .index
        .tolist()
    )

    top5_payments = [cat for cat in top5_cats if cat in current_payment_categories]
    top5_utilities = [cat for cat in top5_cats if cat in current_ui_categories]
    top5_general = [cat for cat in top5_cats if cat in current_expense_categories]

    return top5_payments, top5_utilities, top5_general






# Master select/clear all
@app.callback(
    [Output('breakdown-payments-filter', 'value', allow_duplicate=True),
     Output('breakdown-utilities-insurance-filter', 'value', allow_duplicate=True),
     Output('breakdown-expense-category-filter', 'value', allow_duplicate=True)],
    [Input('select-all-expenses-breakdown-master', 'n_clicks'),
     Input('clear-all-expenses-breakdown-master', 'n_clicks')],
    [State('breakdown-payments-filter-options-store', 'data'),
     State('breakdown-utilities-insurance-filter-options-store', 'data'),
     State('breakdown-expense-category-filter-options-store', 'data')],
    prevent_initial_call=True
)
def toggle_all_expense_breakdown_filters(n_select_all, n_clear_all,
                                         payments_options, utilities_options, categories_options):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'select-all-expenses-breakdown-master':
        return payments_options, utilities_options, categories_options
    elif trigger_id == 'clear-all-expenses-breakdown-master':
        return [], [], []
    return dash.no_update


@app.callback(
    [
        Output('breakdown-payments-filter', 'value', allow_duplicate=True),
        Output('breakdown-utilities-insurance-filter', 'value', allow_duplicate=True),
        Output('breakdown-expense-category-filter', 'value', allow_duplicate=True),
    ],
    [Input('select-top5-expenses-breakdown-master', 'n_clicks')],
    [State('year-radio', 'value'),
     State('month-radio', 'value')],
    prevent_initial_call=True
)
def update_filters_on_select_top5(n_clicks, year, month):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate

    pay, util, gen = auto_select_top5_breakdown_expenses(year, month, "")
    return pay, util, gen



@app.callback(
    [Output('merchant-search-store', 'data'),
     Output('merchant-search', 'value')],
    [
        Input('search-button', 'n_clicks'),
        Input('clear-button', 'n_clicks'),
    ],
    State('merchant-search', 'value'),
    prevent_initial_call=True
)
def update_merchant_search(search_clicks, clear_clicks, search_input):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'clear-button':
        return "", ""  # Clear search store and input field

    elif trigger_id == 'search-button' and search_input:
        return search_input.strip().lower(), search_input

    return dash.no_update, dash.no_update


# Callback for updating the "Top 5 Expenses" pie chart based on the year and month selected
@app.callback(
    Output('top5-expenses-pie-chart', 'figure'),
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')]
)
def update_top5_expenses(year, selected_month):
    # Filter the data by year
    filtered_data = all_expense_data[all_expense_data['Date'].dt.year == year]

    # If a specific month is selected, filter further
    if selected_month != 0:
        filtered_data = filtered_data[filtered_data['Date'].dt.month == selected_month]

    if filtered_data.empty:
        return create_empty_figure(title="Top Expense Categories", message="No data for selected period.")

    # Calculate total expenses for the time period
    total_expense = filtered_data['Amount'].sum()

    # Group by sub-category and calculate total expenses
    expense_by_subcategory = (
        filtered_data.groupby('Sub-Category (Account)')
        .agg({'Amount': 'sum'})
        .reset_index()
    )

    # Get the top 5 expenses
    top5_expenses = expense_by_subcategory.nlargest(5, 'Amount').copy()

    # Calculate % of total for each top 5 category
    top5_expenses['Percent'] = (top5_expenses['Amount'] / total_expense * 100).round(1)

    # Custom label to show: Category Name + % of Total
    top5_expenses['Display'] = top5_expenses.apply(
        lambda row: f"{row['Sub-Category (Account)']}<br>{row['Percent']}%", axis=1
    )

    # Use custom colors for consistency
    pie_colors = [expense_colors.get(cat, '#888') for cat in top5_expenses['Sub-Category (Account)']]

    # Create the pie chart
    fig = go.Figure(data=[go.Pie(
        labels=top5_expenses['Sub-Category (Account)'],
        values=top5_expenses['Amount'],
        text=top5_expenses['Display'], 
        textinfo='text',  
        hovertemplate=(
            "%{label}<br>"
            "$%{value:,.2f} (%{customdata:.1f}%)<extra></extra>"
            ""
        ),
        customdata=top5_expenses['Percent'],
        marker=dict(colors=pie_colors)
    )])

    # Update layout
    title_suffix = f"{calendar.month_name[selected_month]} {year}" if selected_month != 0 else str(year)
    fig.update_layout(
        title=f"Top Expense Categories - {title_suffix}",
        height=550,
        width=650
    )

    return fig



@app.callback(
    Output('top5-purchases-table', 'children'),
    [Input('year-radio', 'value'),
     Input('month-radio', 'value'),
     Input('top5-toggle-mode', 'value')]
)
def update_top5_purchases(selected_year, selected_month, toggle_mode):
    # Filter by selected year and month
    data = all_expense_data[all_expense_data['Date'].dt.year == selected_year].copy()

    if selected_month != 0:
        data = data[data['Date'].dt.month == selected_month]

    if data.empty:
        return dcc.Graph(figure=create_empty_figure(title="Top Transactions", message="No data for selected period."))

    # Replace missing or blank descriptions
    data['Description (Transaction Detail)'] = data.apply(
        lambda row: row['Sub-Category (Account)']
        if pd.isna(row['Description (Transaction Detail)']) or row['Description (Transaction Detail)'].strip().lower() in ["", "nan"]
        else row['Description (Transaction Detail)'],
        axis=1
    )

    # === MODE: BY AMOUNT ===
    if toggle_mode == 'amount':
        top5 = data.nlargest(5, 'Amount')[
            ['Date', 'Description (Transaction Detail)', 'Amount', 'Note / Comment / Memo']
        ].copy()

        # Format
        top5['Date'] = top5['Date'].dt.strftime('%b %d, %Y')
        top5['Amount'] = top5['Amount'].apply(lambda x: f"${x:,.0f}")

        top5 = top5.rename(columns={
            'Description (Transaction Detail)': 'Transaction Detail',
            'Note / Comment / Memo': 'Memo'
        })

        columns = [{'name': col, 'id': col} for col in top5.columns]
        records = top5.to_dict('records')

    # === MODE: BY FREQUENCY ===
    else:
        # Normalize description for matching
        desc_series = data['Description (Transaction Detail)'].str.upper()

        # Identify Amazon/AMZN transactions and tag them
        data['Merchant_Group'] = desc_series.apply(
            lambda x: 'Amazon' if x.startswith('AMAZO') or x.startswith('AMZN') else x[:5].capitalize()
        )

        # Group by first 5 characters
        grouped = data.groupby('Merchant_Group').agg({
            'Description (Transaction Detail)': lambda x: pd.Series(x).mode().iloc[0],
            'Amount': 'sum',
            'Date': 'count'
        }).rename(columns={'Date': '# of Trans'}).reset_index()

        # Sort by frequency, then amount
        top5 = grouped.sort_values(by=['# of Trans', 'Amount'], ascending=[False, False]).head(5)

        # Format the result
        top5['Amount'] = top5['Amount'].apply(lambda x: f"${x:,.0f}")
        top5 = top5.rename(columns={'Description (Transaction Detail)': 'Transaction Detail'})[
            ['# of Trans', 'Transaction Detail', 'Amount']
        ]

        columns = [{'name': col, 'id': col} for col in top5.columns]
        records = top5.to_dict('records')

    return html.Div([
        dash_table.DataTable(
            data=records,
            columns=columns,
            style_table={
                'width': '100%',
                'minHeight': '500px',
                'maxWidth': '100%'
            },
            style_cell={
                'textAlign': 'left',
                'padding': '6px',
                'fontFamily': 'Open Sans',
                'fontSize': '14px',
                'whiteSpace': 'normal',  
                'maxWidth': '200px'  
            },

            style_header={
                'fontWeight': 'bold',
                'fontSize': '16px',
                'backgroundColor': '#f9f9f9',
                'borderBottom': '1px solid #ccc'
            },
            style_data_conditional=[
                {'if': {'column_id': 'Amount'}, 'textAlign': 'center', 'minWidth': '80px'},
                {'if': {'column_id': '# of Trans'}, 'minWidth': '90px', 'textAlign': 'center'},
                {'if': {'column_id': 'Date'}, 'minWidth': '95px'}
            ],
            style_cell_conditional=[
                {'if': {'column_id': 'Transaction Detail'}, 'minWidth': '200px'},
                {'if': {'column_id': 'Date'}, 'minWidth': '95px', 'textAlign': 'center'},
                {'if': {'column_id': '# of Trans'}, 'minWidth': '90px', 'textAlign': 'center'},
                {'if': {'column_id': 'Amount'}, 'minWidth': '80px', 'textAlign': 'center'},
                {'if': {'column_id': 'Memo'}, 'minWidth': '200px'}
            ]
        )
    ])


@app.callback(
    Output('monthly-income-bar-chart', 'figure'),
    [Input('year-radio', 'value'),
     Input('month-radio', 'value'),
     Input('income-type-checklist', 'value')]
)
def update_monthly_income_bar(year, selected_month, selected_accounts):
    if not selected_accounts:
        return create_empty_figure(title='Income Breakdown', message="Please select at least one filter option.")

    # Filter by year and selected income types
    data = income_data[
        (income_data['Date'].dt.year == year) &
        (income_data['Sub-Category (Account)'].isin(selected_accounts))
    ]

    if selected_month != 0:
        # Filter for selected month
        data = data[data['Date'].dt.month == selected_month]

        # Create full date range for selected month
        start_date = pd.Timestamp(year=year, month=selected_month, day=1)
        end_date = start_date + pd.offsets.MonthEnd(0)
        all_days = pd.date_range(start=start_date, end=end_date)

        # Group by full date and account
        grouped = data.groupby([
            data['Date'].dt.date,
            data['Sub-Category (Account)']
        ])['Amount'].sum().reset_index()
        grouped['Date'] = pd.to_datetime(grouped['Date'])

        # Pivot and reindex with all days
        pivot = grouped.pivot(index='Date', columns='Sub-Category (Account)', values='Amount').fillna(0)
        pivot = pivot.reindex(all_days, fill_value=0)
        pivot.index.name = 'Date'

        x_labels = [d.day for d in pivot.index]
        hover_labels = [d.strftime('%b %d') for d in pivot.index]
        title = f"Income Breakdown - {calendar.month_name[selected_month]} {year}"
        xaxis_title = "Day"
    else:
        # Group by month and account
        grouped = data.groupby([
            data['Date'].dt.month,
            data['Sub-Category (Account)']
        ])['Amount'].sum().reset_index()

        pivot = grouped.pivot(index='Date', columns='Sub-Category (Account)', values='Amount').fillna(0)
        pivot.index.name = 'Month'
        pivot = pivot.sort_index()

        x_labels = [calendar.month_abbr[m] for m in pivot.index]
        hover_labels = x_labels
        title = f"Income Breakdown - {year}"
        xaxis_title = "Month"

    # Trend line
    pivot['Total'] = pivot.sum(axis=1)
    avg = pivot['Total'][pivot['Total'] > 0].mean()


    # Build figure
    fig = go.Figure()
    # Sort stack order by total income (largest first)
    stack_order = pivot.drop(columns='Total').sum().sort_values(ascending=False).index.tolist()

    for col in stack_order:
        fig.add_trace(go.Bar(
            x=x_labels,
            y=pivot[col],
            name=col,
            customdata=np.array(hover_labels).reshape(-1, 1),
            marker_color=income_colors.get(col, '#888'),
            hovertemplate='%{customdata[0]}<br>%{fullData.name}: $%{y:,.0f}<extra></extra>'
        ))

    # Add trend line
    fig.add_trace(go.Scatter(
        x=x_labels,
        y=[avg] * len(pivot),
        mode='lines',
        name='Average Income',
        line=dict(color='black', dash='dot'),
        hovertemplate='Average: $%{y:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title="Amount ($)",
        barmode='stack',
        height=500,
        width=700,
        margin=dict(l=60, r=50, t=105, b=50),
        legend=dict(
            orientation='h',
            x=0,
            y=-0.2,
            xanchor='left',
            yanchor='top',
            font=dict(size=12)
        ),
    xaxis=dict(
            tickmode='array',
            tickvals=x_labels,
            tickangle=0,
            tickfont=dict(size=12)
        )

    )

    return fig

@app.callback(
    Output('monthly-expense-bar-chart', 'figure'),
    [
        Input('year-radio', 'value'),
        Input('month-radio', 'value'),
        Input('breakdown-payments-filter', 'value'),
        Input('breakdown-utilities-insurance-filter', 'value'),
        Input('breakdown-expense-category-filter', 'value'),
        Input('merchant-search-store', 'data'),
        Input('search-button', 'n_clicks'),  # triggers updates even on empty results
    ],
    State('merchant-search', 'value'),  
    prevent_initial_call=True
)
def update_monthly_expenses(year, selected_month, payments, utilities, categories, stored_search_value, _, search_input):
    # === Combine selected categories ===
    selected_categories = (payments or []) + (utilities or []) + (categories or [])
    if not selected_categories and not stored_search_value:
        return create_empty_figure(title='Expense Breakdown',
                                   message="Please select at least one filter option or enter a search.")
    # === Build title ===
    month_name = calendar.month_name[selected_month] if selected_month in range(1, 13) else ""
    filter_label = f" - Filter: '{search_input.strip()}'" if search_input and search_input.strip() else ""
    title = f"Expense Breakdown - {month_name} {year}{filter_label}".strip()

    # === Filter data ===
    data = all_expense_data[
        (all_expense_data['Date'].dt.year == year) &
        (all_expense_data['Sub-Category (Account)'].isin(selected_categories))
    ]

    if stored_search_value:
        search_term = stored_search_value.lower().strip()
        data = data[data['Description (Transaction Detail)'].str.lower().str.contains(search_term)]

    if selected_month != 0:
        data = data[data['Date'].dt.month == selected_month]

    if data.empty:
        return create_empty_figure(
            title=f"Expense Breakdown - {month_name} {year}{filter_label}".strip(),
            message="No matching transactions found." if stored_search_value else "No data for selected period."
        )

    # === Group & pivot ===
    if selected_month != 0:
        start_date = pd.Timestamp(year=year, month=selected_month, day=1)
        end_date = start_date + pd.offsets.MonthEnd(0)
        all_days = pd.date_range(start=start_date, end=end_date)

        grouped = data.groupby([
            data['Date'].dt.date,
            data['Sub-Category (Account)']
        ])['Amount'].sum().reset_index()

        pivot = grouped.pivot(index='Date', columns='Sub-Category (Account)', values='Amount').fillna(0)
        pivot = pivot.reindex(all_days, fill_value=0)
        x_labels = [d.day for d in pivot.index]
        hover_labels = [d.strftime('%b %d') for d in pivot.index]
        xaxis_title = "Day"
    else:
        grouped = data.groupby([
            data['Date'].dt.month,
            data['Sub-Category (Account)']
        ])['Amount'].sum().reset_index()

        pivot = grouped.pivot(index='Date', columns='Sub-Category (Account)', values='Amount').fillna(0)
        pivot = pivot.sort_index()
        x_labels = [calendar.month_abbr[m] for m in pivot.index]
        hover_labels = x_labels
        xaxis_title = "Month"

    # === Compute totals & average ===
    pivot['Total'] = pivot.sum(axis=1)
    avg = pivot['Total'][pivot['Total'] > 0].mean()

    # === Create figure ===
    fig = go.Figure()
    stack_order = pivot.drop(columns='Total').sum().sort_values(ascending=False).index.tolist()

    for col in stack_order:
        fig.add_trace(go.Bar(
            x=x_labels,
            y=pivot[col],
            name=col,
            customdata=np.array(hover_labels).reshape(-1, 1),
            marker_color=expense_colors.get(col, '#888'),
            hovertemplate='%{customdata[0]}<br>%{fullData.name}: $%{y:,.0f}<extra></extra>'
        ))

    fig.add_trace(go.Scatter(
        x=x_labels,
        y=[avg] * len(pivot),
        mode='lines',
        name='Average Expense',
        line=dict(color='black', dash='dot'),
        hovertemplate='Average: $%{y:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title="Amount ($)",
        barmode='stack',
        height=500,
        width=700,
        margin=dict(l=60, r=50, t=105, b=50),
        legend=dict(
            orientation='h',
            x=0,
            y=-0.2,
            xanchor='left',
            yanchor='top',
            font=dict(size=12)
        ),
        xaxis=dict(
            tickmode='array',
            tickvals=x_labels,
            tickangle=0,
            tickfont=dict(size=12)
        )
    )

    return fig



@app.callback(
    [
        Output('breakdown-payments-filter', 'value', allow_duplicate=True),
        Output('breakdown-utilities-insurance-filter', 'value', allow_duplicate=True),
        Output('breakdown-expense-category-filter', 'value', allow_duplicate=True),
        Output('merchant-search-store', 'data', allow_duplicate=True),
        Output('merchant-search', 'value', allow_duplicate=True),
    ],
    [
        Input('search-button', 'n_clicks'),
        Input('clear-button', 'n_clicks')
    ],
    [
        State('merchant-search', 'value'),
        State('year-radio', 'value'),
        State('month-radio', 'value')
    ],
    prevent_initial_call=True
)
def update_filters_on_search_or_clear(search_clicks, clear_clicks, search_value, year, month):
    ctx = dash.callback_context

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    triggered_id = ctx.triggered_id

    if triggered_id == 'clear-button':
        # Reset to top 5 with no filter
        pay, util, gen = auto_select_top5_breakdown_expenses(year, month, "")
        return pay, util, gen, "", ""

    if triggered_id == 'search-button' and search_value:
        search_value = search_value.lower().strip()
        filtered = all_expense_data[all_expense_data['Description (Transaction Detail)'].str.lower().str.contains(search_value)]

        if filtered.empty:
            return [], [], [], search_value, search_value

        matched_categories = filtered['Sub-Category (Account)'].unique()

        selected_payments = [cat for cat in matched_categories if cat in sorted_payments]
        selected_utilities = [cat for cat in matched_categories if cat in sorted_utilities_insurance]
        selected_general = [cat for cat in matched_categories if cat in sorted_expenses]

        return selected_payments, selected_utilities, selected_general, search_value, search_value

    raise dash.exceptions.PreventUpdate

@app.callback(
    [
        Output('breakdown-payments-filter', 'value', allow_duplicate=True),
        Output('breakdown-utilities-insurance-filter', 'value', allow_duplicate=True),
        Output('breakdown-expense-category-filter', 'value', allow_duplicate=True),
        Output('merchant-search-store', 'data', allow_duplicate=True),
        Output('merchant-search', 'value', allow_duplicate=True),
    ],
    [Input('year-radio', 'value'),
     Input('month-radio', 'value')],
    [State('merchant-search', 'value')],
    prevent_initial_call=True
)
def update_expense_filters_on_date_change(year, month, search_value):
    ctx = dash.callback_context

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    triggered_id = ctx.triggered_id

    # If user has entered a search value, re-filter the expense categories for the new month/year
    if triggered_id in ['month-radio', 'year-radio'] and search_value and search_value.strip():
        search_value = search_value.lower().strip()

        # Filter for search match using updated year/month
        filtered = all_expense_data[
            (all_expense_data['Date'].dt.year == year) &
            ((all_expense_data['Date'].dt.month == month) if month != 0 else True) &
            all_expense_data['Description (Transaction Detail)'].str.lower().str.contains(search_value)
        ]

        if filtered.empty:
            return [], [], [], search_value, search_value

        matched_categories = filtered['Sub-Category (Account)'].unique()

        selected_payments = [cat for cat in matched_categories if cat in sorted_payments]
        selected_utilities = [cat for cat in matched_categories if cat in sorted_utilities_insurance]
        selected_general = [cat for cat in matched_categories if cat in sorted_expenses]

        return selected_payments, selected_utilities, selected_general, search_value, search_value

    raise dash.exceptions.PreventUpdate


if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True)
###



