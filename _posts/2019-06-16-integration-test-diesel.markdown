---
layout: "post"
title: "Testing with a database - Usecase with Diesel"
date: 2019-06-16
---

Testing is important. As complexity builds up in an application, it is also very easy to give up automated testing. The tests are more and more complicated to create and maintain, tests work on local machines with custom setup up but fail every now and then on CI tools...

Today I won't try to solve all these issues (sorry), but I'll show an easy way to do integration testing with a real database. I'll write about diesel, migrations, test strategy and RAII in rust so if any of these topics interests you, stay tuned!

## Setting up a Diesel project

You can quickly set up a project that uses a database with [Diesel](http://diesel.rs/guides/getting-started/). In my case, I use postgres so I only applied the postgres specific steps.

You'll need a database. I'm using docker-compose to start a postgres database and a GUI (adminer) to explore the tables. Feel free to use it.

```yml
version: '3.1'

services:

  db:
    image: postgres
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: example
    ports:
      - 5432:5432

  adminer:
    image: adminer
    restart: always
    ports:
      - 8081:8080
```

This post is not about using Diesel (more like testing diesel) so I'll assume that you'll have an User table for the next steps.

This is my user structure by the way:

```rust

/// Represent an user for our application.
#[derive(Debug, Queryable)]
#[table_name = "users"]
pub struct User {
    pub id: i32,
    pub email: String,
    pub name: String,
    pub password: String,
}

impl User {
    /// Return an user by its ID. It might return no user if there
    /// is no match. In that case, Result is None.
    /// 
    pub fn get_user_by_email(
        conn: &PgConnection,
        email: String,
    ) -> Option<User> {
        use crate::schema::users::dsl::*;
        users
            .filter(email.eq(email))
            .first(conn)
            .optional().unwrap()
    }
}

```

## Test strategy

For integration tests, I want to do the testing as close as it will be in reality. The database will be similar to production database. One way to separate integration testing from production is simply to have a database dedicated to testing.

Tests can also be done in parallel so that it takes less time to run the test suite. For that reason, I cannot use the same database for all tests. Each test will have its own database. Each test will also clean up nicely after it is done so that we don't have hundred of databases after executing the test suite.

To summarize:
- Each test will have its own database
- Before a test begins, a database will be created and all the migrations will be applied
- After a test ends, the database will be dropped.

## No fixture? Drop trait at the rescue

Rust does not really provide a testing framework with fixture and mocking so I need to implement my own fixtures. A popular pattern is to use the Drop trait to tear-up resources when the test ends.

Basically, you create an object that will set up resources. Let's call it a `TestContext`. This object will implement the `Drop` trait, so when it goes out of scope, his `drop` method will be called and will clean up the resources. This is similar to RAII in c++.

In practice,

```rust

struct TestContext {}

impl TestContext {

        fn new() -> Self {
                println!("Set up resources");
                Self {}
        }

}

impl Drop for TestContext {
        fn drop(&mut self) {
                println!("Clean up resources");
        }
}


#[test]
fn try_it() {
        // Needs to be created first.
        let _ctx = TestContext::new();

        // Do your test here
}
```

## Setup/Cleanup database

Now I can fill the `new` and `drop` functions. 

`new` will connect to `postgres` database which is a default database in Postgres. It is used when you don't have a database yet but want to execute some SQL. Then it will execute some raw SQL to create a new test database.

It looks likes:

```rust

// Keep the databse info in mind to drop them later
struct TestContext {
        base_url: String,
        db_name: String,
        }

impl TestContext {
        fn new(base_url: &str, db_name: &str) -> Self {
                // First, connect to postgres db to be able to create our test
            // database.
            let postgres_url = format!("{}/postgres", base_url);
            let conn =
                PgConnection::establish(&postgres_url).expect("Cannot connect to postgres database.");

            // Create a new database for the test
            let query = diesel::sql_query(format!("CREATE DATABASE {}", db_name).as_str());
            query
                .execute(&conn)
                .expect(format!("Could not create database {}", db_name).as_str());


                Self {
                        base_url: base_url.to_string(),
                        db_name: db_name.to_string(),
                }
        }        
}
```

`drop` will drop the database.

```rust

impl Drop for TestContext {

    fn drop(&mut self) {
        let postgres_url = format!("{}/postgres", self.base_url);
        let conn =
            PgConnection::establish(&postgres_url).expect("Cannot connect to postgres database.");

        let disconnect_users = format!(
            "SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '{}';",
            self.db_name
        );

        diesel::sql_query(disconnect_users.as_str())
            .execute(&conn)
            .unwrap();


        let query = diesel::sql_query(format!("DROP DATABASE {}", self.db_name).as_str());
        query
            .execute(&conn)
            .expect(&format!("Couldn't drop database {}", self.db_name));
    }
}

```

There is some specific code for postgres. Postgres will refuse to delete a database if there is any connected user. It's possible depending on your test that a connection is still opened to the database. In that case, the SQL query supplied above will mercilessly disconnect them from the database.


Now, if you run the test now, it should create a database and remove it as expected. Comment out the drop implementation if you need some convincing ;).

Next step is to run the migrations so that the users table will be available during the test. There is a crate named `diesel-migrations` that contains a macro to execute the migrations in a specific folder. So add `diesel_migrations = "1.4.0"` to your Cargo file, and add:

```rust
#[macro_use]
extern crate diesel_migrations;
use diesel_migrations::embed_migrations;

embed_migrations!("migrations/");

```

Where `migrations` is the folder created by the diesel cli.
Now, you just have to connect to your new database and use `embed_migrations` to run the migrations.

```rust

// .... in new
    // Now we can connect to the database and run the migrations
    let conn = PgConnection::establish(&format!("{}/{}", base_url, db_name))
        .expect(&format!("Cannot connect to {} database", db_name));

    embedded_migrations::run(&conn);
// ....
```

And this is it! You can run integration tests that include a database connection without having to worry. I'm pretty sure all of this is can be used with various database backends but I'll leave that exercise to the reader.

```rust
#[test]
fn insert_user_test() {
    let _ctx = setup_database("postgres://postgres:example@127.0.0.1", "sometest1");

    let conn = PgConnection::establish(&format("postgres://postgres:example@127.0.0.1/sometest1"))
        .unwrap();

    // Now do your test.
    diesel::sql_query(
        "INSERT INTO users (email, name, password) VALUES ('MAIL', 'NAME', 'PASSWORD')",
    )
    .execute(&conn)
    .unwrap();
    let u = User::get_user_by_email(&conn, "MAIL".to_string())
        .unwrap()
        .unwrap();

    assert_eq!(u.name, "NAME".to_string());
    assert_eq!(u.password, "PASSWORD".to_string());
}


#[test]
fn remove_user_test() {
    let _ctx = setup_database("postgres://postgres:example@127.0.0.1", "sometest2");

    let conn = PgConnection::establish(&format("postgres://postgres:example@127.0.0.1/sometest2"))
        .unwrap();


        // Run the test ...

}

```

Oh and by the way, if you want to use the TestContext in multiple test files, you will need to put it as common code. Because every file in `tests/` is compiled as a single crate, you will need to put the common code in `tests/common/mod.rs` and add the common module to each of your test files.
