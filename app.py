import streamlit as st
import pickle
import pandas as pd
import requests

def fetch_poster(movie_id):
    response = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=997c27f7f3caa964aa552d3cc03ed5c7')
    data = response.json()
    return "http://image.tmdb.org/t/p/w500/" + data['poster_path']

def recommended(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]
    movie_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    names, posters = [], []
    for i in movie_list:
        movie_id = movies.iloc[i[0]].movie_id
        names.append(movies.iloc[i[0]].title)
        posters.append(fetch_poster(movie_id))
    return names, posters

# Load data
movies = pd.DataFrame(pickle.load(open('movies_dict.pkl', 'rb')))
similarity = pickle.load(open('similarity_dict.pkl', 'rb'))

# Streamlit app
st.title('Movie Recommender System')

selected_movie_name = st.selectbox('Select a Movie', movies['title'].values)

if st.button('Recommend'):
    names, posters = recommended(selected_movie_name)

    # Display recommendations
    cols = st.columns(5)
    for col, name, poster in zip(cols, names, posters):
        with col:
            st.text(name)
            st.image(poster)