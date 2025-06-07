import mysql.connector as db
import pandas as pd
import streamlit as st 
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

def get_db_connection():
    db_con = db.connect(
	host = 'localhost',
	user = 'rino',
	password = 'admin@123',
	database = 'mydb'
    )
    return db_con

def format_duration(minutes):
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours} : {mins}" 

# ================ Filter functionality starts ====================
main_query = "SELECT MOVIE_NAME AS Movies, GENRE AS Genre, RATINGS AS Ratings, VOTING_COUNTS AS Votes, DURATION AS 'Duration' FROM MOVIE_DATA"
where_conditions = []
params = []
operator_map = {"Greater": ">", "Lesser": "<", "Equal": "="}

st.sidebar.header("Find Movies")

# Genre
with st.sidebar:
    genre_col1, genre_col2 = st.columns([1, 2])
    with genre_col1:
        st.markdown("### Genre")
    with genre_col2:
        genre = st.multiselect(
            "", 
            ["Action", "Romance", "Comedy", "Crime", "Fantasy"], 
            key="genre", 
            label_visibility="collapsed"
        )


# Duration filter:
with st.sidebar:
    st.markdown("### Duration") 
    duration_operator = st.selectbox("Operator", ["", "Greater", "Lesser", "Equal", "Between"], key="duration_op")
    
    if duration_operator == "Between":
        duration_min = st.selectbox("From (hours)", ["", 1, 2, 3], key="duration_min")
        duration_max = st.selectbox("To (hours)", ["", 1, 2, 3], key="duration_max")
    else:
        duration_value = st.selectbox("Value (hours)", ["", 1, 2, 3], key="duration_val")


# Votes filter:
with st.sidebar:
    st.markdown("### Votes")
    vote_col1, vote_col2 = st.columns([1, 2])
    with vote_col1:
        votes_operator = st.selectbox("Operator", ["","Greater", "Lesser", "Equal"], key="votes_op")
    with vote_col2:
        votes_value = st.number_input("Value", min_value=0, step=1000, key="votes_val")


# Rating filter:
st.sidebar.markdown("### Rating")
rate_col1, rate_col2 = st.sidebar.columns([1, 2])
with rate_col1:
    rating_operator = st.selectbox("Operator", ["","Greater", "Lesser", "Equal"], key="rating_op")
with rate_col2:
    rating_value = st.number_input("Value", min_value=0.0, max_value=10.0, step=0.1, format="%.1f", key="rating_val")

# Search Button
search_button = st.sidebar.button("Search")

# Genre Filter query
if genre:
    param_holders = ", ".join(["%s"] * len(genre))
    genre_condition = f"UPPER(GENRE) IN ({param_holders})"
    where_conditions.append(genre_condition)
    params.extend([g.upper() for g in genre])


# Duration filter query
if duration_operator == "Between":
    if duration_min != "" and duration_max != "" and duration_min > duration_max:
        st.warning("Maximum duration should be greater than minimum duration.")
        st.stop()
    if duration_min != "" and duration_max != "":
        min_minutes = duration_min * 60
        max_minutes = duration_max * 60
        where_conditions.append("DURATION BETWEEN %s AND %s")
        params.extend([min_minutes, max_minutes])
elif duration_operator in operator_map and duration_value != "":
    where_conditions.append(f"DURATION {operator_map[duration_operator]} %s")
    params.append(duration_value * 60)


# Votes filter query
if votes_operator in operator_map:
    where_conditions.append(f"VOTING_COUNTS {operator_map[votes_operator]} %s")
    params.append(votes_value)


# Rating filter query
if rating_operator in operator_map:
    where_conditions.append(f"RATINGS {operator_map[rating_operator]} %s")
    params.append(rating_value)


if where_conditions:
    filter_query = main_query + " WHERE " + " AND ".join(where_conditions)
else:
    filter_query = main_query

if search_button:
    db_con = get_db_connection()
    curr = db_con.cursor()
    curr.execute(filter_query, params)
    rows = curr.fetchall()
    col = curr.column_names
    df = pd.DataFrame(rows, columns=col)
    df['Duration'] = df['Duration'].apply(format_duration)
    st.subheader("Filtered Movies List") 
    st.dataframe(df)
    curr.close()
    db_con.close()

# ================ Filter functionality Ends ====================

# ================ Data Visualization Starts ====================

query = "SELECT * FROM MOVIE_DATA"
db_con = get_db_connection()
curr = db_con.cursor()
curr.execute(query)
data = curr.fetchall()
col = curr.column_names
df = pd.DataFrame(data,columns=col)

curr.close()
db_con.close()

# 1.Top 10 movies
prct_90 = df['VOTING_COUNTS'].quantile(0.90)
df_prct_90 = df[df['VOTING_COUNTS'] > prct_90]

grouped_df = df_prct_90.groupby('MOVIE_NAME').agg({
    'RATINGS': 'max',
    'VOTING_COUNTS': 'max',
    'GENRE': lambda x: ','.join(x),
    'DURATION': 'first'
}).reset_index()

top_10_movies = grouped_df.sort_values(by=['RATINGS', 'VOTING_COUNTS'], ascending=False).head(10)
top_10_movies['DURATION'] = top_10_movies['DURATION'].apply(format_duration)
st.subheader("Top 10 Rated Movies")
st.dataframe(top_10_movies.reset_index(drop=True))

# 2.Movies per each genre in a bar chart
genre_counts = df['GENRE'].value_counts().reset_index()
print(genre_counts)
genre_counts.columns = ['GENRE','COUNT']
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(data=genre_counts, x='GENRE', y='COUNT', ax=ax, palette='muted')
ax.set_xlabel("Genre")
ax.set_ylabel("Movie Count")
ax.set_facecolor("ivory")
ax.set_title("Number of Movies per Genre")
st.pyplot(fig)

# 3.Average Duration by Genre
avg_duration = df.groupby('GENRE')['DURATION'].mean().sort_values().reset_index()
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(data=avg_duration, y='GENRE', x='DURATION', ax=ax, palette='crest')
ax.set_xlabel("Average Duration (minutes)")
ax.set_ylabel("Genre")
ax.set_facecolor("seashell")
ax.set_title("Average Movie Duration by Genre")
st.pyplot(fig)

# 4.Average Voting Counts by Genre
avg_votes = df.groupby('GENRE')['VOTING_COUNTS'].mean().sort_values(ascending=False).reset_index()
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(data=avg_votes, x='GENRE', y='VOTING_COUNTS', ax=ax, palette='dark:#5A9')
ax.set_ylabel("Average Number of Votes")
ax.set_xlabel("Genre")
ax.set_facecolor("aliceblue")
ax.set_title("Average Voting Counts by Genre")
st.pyplot(fig)

# 5.Rating Distribution using histogram
fig, ax = plt.subplots(figsize=(12, 6))
sns.histplot(data=df, x='RATINGS', bins=20, kde=False, color='lavender', edgecolor='black', ax=ax)
ax.set_xlabel("Rating")
ax.set_ylabel("No of Movies")
ax.set_title("Histogram of Movie Ratings")
ax.set_facecolor("ivory")
st.pyplot(fig)

# 6.Genre-Based Rating Leaders
st.subheader("Top Rated Movies Based On Genre")
df_sorted = df.sort_values(by='RATINGS', ascending=False)
top_per_genre = df_sorted.drop_duplicates(subset='GENRE', keep='first')
display_df = top_per_genre[['GENRE', 'MOVIE_NAME', 'RATINGS']].reset_index(drop=True)
display_df.columns = ['Genre', 'Top Movie', 'Rating']
st.table(display_df)

# 7.Most Popular Genres by Voting
genre_votes = df.groupby('GENRE')['VOTING_COUNTS'].sum().sort_values(ascending=False).reset_index()
fig = px.pie(
    genre_votes,
    names='GENRE',
    values='VOTING_COUNTS',
    title='Most Popular Genres by Voting',
    color_discrete_sequence=px.colors.qualitative.Pastel1
)
st.plotly_chart(fig, use_container_width=True)

# 8.Duration Extremes (Shortest and Longest)
st.subheader("Duration Extremes")
shortest = df.loc[df['DURATION'].idxmin()]
longest = df.loc[df['DURATION'].idxmax()]

df_min_max_duration = pd.DataFrame([
    {"Type": "Shortest", "Movie": shortest['MOVIE_NAME'], "Duration (min)": shortest['DURATION']},
    {"Type": "Longest", "Movie": longest['MOVIE_NAME'], "Duration (min)": longest['DURATION']}
])
st.table(df_min_max_duration)

# 9.Avg Ratings by Genre Using HeatMap
st.subheader("Avg Ratings by Genre")
df['RATINGS'] = pd.to_numeric(df['RATINGS'])
avg_ratings = df.groupby('GENRE')['RATINGS'].mean().sort_values()
heat_df = avg_ratings.to_frame().T
fig, ax = plt.subplots(figsize=(12, 2))
sns.heatmap(heat_df, annot=True, cmap='YlGnBu', fmt=".1f", linewidths=1, ax=ax)
ax.set_title("Avg Ratings by Genre")
st.pyplot(fig)

# 10.Correlation Analysis
st.subheader("Correlation Analysis")
df['RATINGS'] = pd.to_numeric(df['RATINGS'])
df['VOTING_COUNTS'] = pd.to_numeric(df['VOTING_COUNTS'])
fig, ax = plt.subplots(figsize=(10, 6))
sns.scatterplot(
    data=df,
    x='VOTING_COUNTS',
    y='RATINGS',
    alpha=0.6,
    color='royalblue'
)
ax.set_title("Ratings vs Voting Counts")
ax.set_xlabel("Voting Counts")
ax.set_ylabel("Ratings")
st.pyplot(fig)

corr = df['RATINGS'].corr(df['VOTING_COUNTS'])
st.markdown(f"Correlation coefficient:{corr:.2f}")

