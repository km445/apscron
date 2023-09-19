{% if session_data %}
let token = {{ session_data.get("token")|tojson }};
let user = {{ session_data.get("user")|tojson }};
{% else %}
let token = "";
let user = "";
{% endif %}

{% raw %}
Vue.prototype.$isSubmitDisabled = false;

Vue.mixin({
    methods: {
        getSortArrow(value) {
            return value ? '↓' : '↑'
        },
        getEnterText(value) {
            return value ? 'Enter from-to' : 'Enter value'
        },
        showMessage(text, variant, title){
            this.$bvToast.toast(
                text,
                {
                    solid: true,
                    title: title,
                    variant: variant,
                    autoHideDelay: 3000
                }
            )
        },
        getAdaptedFilters(filters){
            let adaptedFilters = {};
            for (const [filter_key, filter_settings] of Object.entries(filters)) {
                if (filter_settings.value) {
                    if (filter_settings.type === "daterange" && filter_settings.value.start && filter_settings.value.end){
                        adaptedFilters[filter_key] = `${filter_settings.value.start} - ${filter_settings.value.end}`;
                    }
                    if (filter_settings.type === "select" && filter_settings.value.length){
                        let values = filter_settings.value.map(val => val.id);
                        adaptedFilters[filter_key] = values.join(",");
                    }
                    if (filter_settings.type === "text" && filter_settings.value){
                        adaptedFilters[filter_key] = filter_settings.value;
                    }
                }
            }
            return adaptedFilters
        },
        userHasAccess(permission){
            if (user && user.permissions && user.permissions.includes(permission)){
                return true
            } else {
                return false
            }
        },
        getItems(url, filters){
            let data = {};
            axios.get(url).then(
                response => {
                    data = response.data.data.items;
                    return data
                }
            ).catch(
                e => {
                    console.log(e)
                }
            );
        },
        getUser(){
            return user
        },
        logout(){
            axios.post(
                "/auth/logout",
            ).then(
                response => {
                    if(response.data.ok){
                        setTimeout(() => {window.location = "/front/login"}, 1000);
                    };
                }
            )
        }
    },
    filters: {
        cutText(string, maxLength = 20) {
            return string.length < maxLength ? string : string.slice(0, maxLength) + '...'
        }
    },
    created(){
        let vueContext = this;
    }
})

const vm = new Vue({});

function showMessages(messages){
    if (messages && messages.length){
        messages.forEach(message => vm.showMessage(message.message, message.variant, message.title));
    }
}

axios.interceptors.response.use(function (response) {
    let messages = response.data.messages;
    showMessages(messages);
    return response;
}, function (error) {
    if (error.response) {
        let messages = error.response.data.messages;
        showMessages(messages);
        if (error.response.status === 401) {
            setTimeout(() => {window.location = "/front/login"}, 1000);
        }
    } else {
        vm.showMessage(error.message, "danger", "Error");
    }
    return Promise.reject(error);
});

if (token){
    axios.interceptors.request.use(function (config) {
    config.headers.Authorization =  `Bearer ${token}`;
    return config;
  });
}
{% endraw %}
