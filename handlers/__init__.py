from handlers.admin import router as admin_router
from handlers.games import router as games_router
from handlers.general import router as general_router

all_routers = [admin_router, games_router, general_router]
