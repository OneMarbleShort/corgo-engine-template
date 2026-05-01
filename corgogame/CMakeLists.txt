cmake_minimum_required(VERSION 3.24)
set(CMAKE_C_STANDARD 11)

project(CorgoGame C ASM)

include(FetchContent)

FetchContent_Declare(
  CorgoEngine
  GIT_REPOSITORY https://github.com/karurosu/corgo-engine.git
  GIT_TAG main
  SOURCE_DIR ${CMAKE_SOURCE_DIR}/../corgo-engine
)

FetchContent_MakeAvailable(CorgoEngine)

ce_add_playdate_game(NAME corgogame)
