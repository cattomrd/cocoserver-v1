from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
load_dotenv()
# Configuración de la base de datos
SQLALCHEMY_DATABASE_URL = "sqlite:///./RaspDatos.db"

# Para una base de datos PostgreSQL, usa:
#SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

#user_db = os.environ.get('POSTGRES_USER')
#password_db = os.environ.get('POSTGRES_PASSWORD')
#db = os.environ.get('POSTGRES_DB')
#server_db = os.environ.get('POSTGRES_HOST')

#SQLALCHEMY_DATABASE_URL = f"postgresql://{user_db}:{password_db}@{server_db}/{db}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()