{% raw %}
Vue.prototype.$permissions = {
    userLoginView: "post_login_view",
    userLogoutView: "post_logout_view",
    userListView: "get_users_view",
    userAddView: "post_users_view",
    userGetView: "get_user_view",
    userEditView: "put_user_view",
    userDeleteView: "delete_user_view",
    userLogView: "get_user_log_view",
    jobListView: "get_jobs_view",
    jobAddView: "post_jobs_view",
    jobGetView: "get_job_view",
    jobEditView: "put_job_view",
    jobDeleteView: "delete_job_view",
    jobPauseView: "post_pause_job_view",
    jobLogView: "get_job_log_view",
    errorLogView: "get_error_log_view",
};
{% endraw %}
