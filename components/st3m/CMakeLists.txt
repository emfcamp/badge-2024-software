set(ST3M_VERSION_PATH "${CMAKE_CURRENT_BINARY_DIR}/include/st3m_version.c")

if (NOT EXISTS "${CMAKE_CURRENT_BINARY_DIR}/include/")
    file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/include/")
endif()

idf_component_register(
    SRCS
        st3m_counter.c
        st3m_imu.c
        "${ST3M_VERSION_PATH}"
    INCLUDE_DIRS
        .
    REQUIRES
        flow3r_bsp
        ctx
        esp_timer
)

# Generate st3m_version.c
add_custom_command(
    OUTPUT
        "${ST3M_VERSION_PATH}"
        "${ST3M_VERSION_PATH}.fake"
    COMMAND
        "${python}" "${CMAKE_CURRENT_SOURCE_DIR}/host-tools/version.py" "-c" > "${ST3M_VERSION_PATH}.tmp"
    COMMAND
        ${CMAKE_COMMAND} -E copy_if_different "${ST3M_VERSION_PATH}.tmp" "${ST3M_VERSION_PATH}"
    COMMAND
        ${CMAKE_COMMAND} -E remove "${ST3M_VERSION_PATH}.tmp"
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generate st3m_version.c"
    VERBATIM
)
add_custom_target(generate_st3m_version_c ALL DEPENDS "${ST3M_VERSION_PATH}")
idf_component_get_property(st3m_lib st3m COMPONENT_LIB)
add_dependencies("${st3m_lib}" generate_st3m_version_c)
