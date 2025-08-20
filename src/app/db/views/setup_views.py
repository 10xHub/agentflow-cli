from tortoise import Tortoise


crosstab = "CREATE EXTENSION IF NOT EXISTS tablefunc;"


async def setup_view():
    """
    Sets up the database view if it does not already exist.

    This function checks if a specific view exists in the database. If the view
    does not exist, it executes a script to create the view.

    Returns:
        None

    Raises:
        Exception: If there is an issue with the database connection or query execution.
    """
    # get connection
    connection = Tortoise.get_connection(connection_name="default")

    # ************************************************************
    # ******************* View Name ****************
    # ************************************************************
    sql = (
        "SELECT EXISTS (SELECT table_name FROM information_schema.views"
        "WHERE table_name = 'view_name')"
    )
    res = await connection.execute_query(sql)
    status = res[1][0]["exists"]
    if not status:
        await connection.execute_script(crosstab)
        # view not exits; let's create all the views
        # await connection.execute_script(v_jd_history)
