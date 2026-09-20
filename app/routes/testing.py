from fastapi import APIRouter

# /testing is now served by the React app (frontend/src/pages/Testing.tsx),
# retired here once the React page was validated as equivalent.
router = APIRouter()


# Examples
# @router.get("/testing")
# def testing_page():
#     ...

# @router.post("/testing")
# def run_test():
#     ...