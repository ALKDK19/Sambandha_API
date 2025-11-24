from sqlalchemy.ext.declarative import as_declarative


@as_declarative()
class Base:
    id: int
    __name__: str

    # Generate __tablename__ automatically
    def __tablename__(self) -> str:
        return self.__name__.lower()
