{% raw %}
Vue.prototype.$apiRoutes = {
    loginView: "/auth/login",
    logoutView: "/auth/logout",
    usersView: "/users",
    userView: "/users/",
    jobsView: "/jobs",
    jobView: "/jobs/",
    pauseJobView: "/jobs/pause/",
    jobLogView: "/logs/jobs",
    userLogView: "/logs/users",
    errorLogView: "/logs/errors",
    jobCommonDataView: "/jobs_common_data",
    userCommonDataView: "/users_common_data",
};

Vue.prototype.$frontRoutes = {
    loginView: "/front/login",
    usersView: "/front/users",
    addUserView: "/front/users/add",
    userView: "/front/users/",
    jobsView: "/front/jobs",
    addJobView: "/front/jobs/add",
    jobView: "/front/jobs/",
    jobLogView: "/front/logs/jobs",
    userLogView: "/front/logs/users",
    errorLogView: "/front/logs/errors",
    errorView: "/front/error",
};
{% endraw %}
