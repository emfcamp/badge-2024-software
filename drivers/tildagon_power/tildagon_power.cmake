# Create an INTERFACE library for our C module.
add_library(usermod_tildagon_power INTERFACE)


# Add our source files to the lib
target_sources(usermod_tildagon_power INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/tildagon_power.c
    ${CMAKE_CURRENT_LIST_DIR}/bq25895/bq25895.c
    ${CMAKE_CURRENT_LIST_DIR}/fusb302b/fusb302b.c
    ${CMAKE_CURRENT_LIST_DIR}/fusb302b/fusb302b_pd.c
    ${CMAKE_CURRENT_LIST_DIR}/mp_power.c
    ${CMAKE_CURRENT_LIST_DIR}/mp_power_event.c
)

# Add the current directory as an include directory.
target_include_directories(usermod_tildagon_power INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/bq25895
    ${CMAKE_CURRENT_LIST_DIR}/fusb302b
)

# Link our INTERFACE library to the usermod target.
target_link_libraries(usermod INTERFACE usermod_tildagon_power)