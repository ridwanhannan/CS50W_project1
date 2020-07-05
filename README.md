# Project 1

Web Programming with Python and JavaScript

This project for CS50W is a book review application which I called "Bookclub" In this application users can register in order to view details about books as well as their ratings via Goodreads API. Users can also leave a review and a rating on a book of their choice.

The flask application functions through application.py which manages requests and routes. import.py was used to import a databse of 5000 books from a csv file into a sql database that could then be queried and displayed on the web application. the templates file contains. the html files that are rendered at various routes from application.py. static includes images used on the webpage as well as the cascading style sheet to style the html elements. helpers.py contains a login-login_required function that was referenced from the internet and used in the flask application.py
