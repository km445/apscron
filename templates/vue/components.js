{% raw %}

Vue.component('vue-ctk-date-time-picker', window['vue-ctk-date-time-picker']);
Vue.component("vue-json-pretty", VueJsonPretty.default);

Vue.component('user-form', {
    props: {user: Object, permissions: Array, isUpdate: Boolean, cancelTo: String},
    data() {
        return {
            isSubmitDisabled: false
        }
    },
    template:
        `<div>
            <h5 class="text-center">{{isUpdate ? 'Edit user ' + user.username : 'Add user'}}</h5>
            <b-form method="POST">
                <b-form-group id="" label="Username:" label-for="user-username" description="">
                    <b-form-input id="user-username" v-model="user.username" type="text" placeholder="Enter username" name="username" required></b-form-input>
                </b-form-group>
                <b-form-group id="" label="User password:" label-for="user-password" description="">
                    <b-form-input id="user-password" v-model="user.password" type="password" :placeholder="isUpdate ? 'Leave empty to keep old password' : 'Enter user password'" name="password" :required="isUpdate ? false : true"></b-form-input>
                </b-form-group>
                <b-form-group id="" label="User allowed IP list:" label-for="user-ip-list" description="">
                    <b-form-input id="user-ip-list" v-model="user.ip_list" type="text" placeholder="Enter JSON-serialized IP list " name="ip_list"></b-form-input>
                </b-form-group>
                <b-form-group id="" label="User authenticator code:" label-for="user-gauth" description="">
                    <b-form-input id="user-gauth" v-model="user.gauth" type="text" :placeholder="isUpdate ? 'Leave empty to keep old authenticator code' : 'Enter user authenticator code'" name="gauth" :required="isUpdate ? false : true"></b-form-input>
                </b-form-group>
                <b-form-group label="User permissions">
                    <b-form-checkbox switch inline
                        v-for="permission in permissions"
                        v-model="user.permissions"
                        :key="permission.id"
                        :value="permission.name"
                        name="permissions">
                        {{ permission.label }}
                    </b-form-checkbox>
                </b-form-group>
                <b-form-group id="" label="User is admin:" label-for="user-is-admin" description="">
                    <b-form-checkbox v-model="user.is_admin" name="is_admin" id="user-is-admin" switch false-value="''">
                    </b-form-checkbox>
                </b-form-group>
                <b-form-group id="" label="User is active:" label-for="user-is-active" description="">
                    <b-form-checkbox v-model="user.is_active" name="is_active" id="user-is-active" switch false-value="''">
                    </b-form-checkbox>
                </b-form-group>
                <div class="text-center mb-3">
                    <b-button @click="submit" :disabled="isSubmitDisabled" type="button" variant="primary">Save</b-button>
                    <b-button variant="danger" :href="cancelTo">Cancel</b-button>
                </div>
            </b-form>
        </div>`,
    methods: {
        submit() {
            this.isSubmitDisabled = true;
            try {
                var user_data = JSON.parse(JSON.stringify(this.user));
                user_data.ip_list = JSON.parse(this.user.ip_list);
            } catch (e) {
                this.showMessage("Invalid user data", "danger", "Error");
                this.isSubmitDisabled = false;
                return
            }
            if(this.isUpdate){
                axios.put(
                    `${this.$apiRoutes.userView}${this.user.id}`,
                    user_data
                ).then(
                    response => {
                        setTimeout(() => {window.location = this.$frontRoutes.usersView}, 1000);
                    }
                ).catch(
                    e => {
                        this.isSubmitDisabled = false;
                        console.log(e)
                    }
                )
            } else {
                axios.post(
                    this.$apiRoutes.usersView,
                    user_data
                ).then(
                    response => {
                        setTimeout(() => {window.location = this.$frontRoutes.usersView}, 1000);
                    }
                ).catch(
                    e => {
                        this.isSubmitDisabled = false;
                        console.log(e)
                    }
                )
            }
        },
    }
});

Vue.component('job-form', {
    components: {
        Multiselect: window.VueMultiselect.default
    },
    data() {
        this.triggerDescription = null;
        this.moduleDescription = null;
        return {
            isSubmitDisabled: false,
            triggerDescription: this.triggerDescription,
            moduleDescription: this.moduleDescription,
        }
    },
    props: {job: Object, jobTriggers: Array, availableJobs: Array, isUpdate: Boolean, cancelTo: String},
    template:
        `<div>
            <h5 class="text-center">{{isUpdate ? 'Edit job ' + job.id : 'Add job'}}</h5>
            <b-form ref="form">
                <b-form-group id="" label="Job name:" label-for="job-name" description="">
                    <b-form-input id="job-name" v-model="job.name" type="text" placeholder="Enter job name" name="job_name" required></b-form-input>
                </b-form-group>
                <b-form-group id="" label="Job parameters/JSON config. Has to be valid JSON object." label-for="job-kwargs" description="">
                    <b-form-textarea id="job-kwargs" v-model="job.kwargs" placeholder="Job parameters/JSON config. Has to be valid JSON." name="job_kwargs" required></b-form-textarea>
                </b-form-group>
                <b-form-group id="" label="Job module:" label-for="job-module">
                    <b-form-select
                        id="job-module"
                        name="job_module"
                        v-model="job.module"
                        :options="availableJobs"
                        class="mb-3"
                        value-field="name"
                        text-field="label"
                        required>
                    </b-form-select>
                    <div v-html="getModuleDescription()">
                    </div>
                </b-form-group>
                <b-form-group id="" label="Job trigger/schedule:" label-for="job-trigger" :description="getTriggerDescription()">
                    <b-form-select
                        id="job-trigger"
                        name="job_trigger"
                        v-model="job.trigger"
                        :options="jobTriggers"
                        class="mb-3"
                        value-field="name"
                        text-field="label"
                        required>
                    </b-form-select>
                </b-form-group>
                <b-form-group id="" v-if="job.trigger == 'date'" label="Select date:" label-for="job-runDate"
                    description="Warning: empty run date means that job executes immediately">
                    <vue-ctk-date-time-picker
                        :id="'job-runDate'"
                        :name="'run_date'"
                        v-model="job.run_date"
                        :format="'YYYY-MM-DD HH:mm:ss'"
                        :formatted="'YYYY-MM-DD HH:mm:ss'"
                        :no-label="true"
                        :label="'Select date'"/>
                </b-form-group>
                <b-form-group id="" v-if="job.trigger == 'interval'" label="Select interval:" label-for="job-interval">
                    <b-row id="job-interval">
                        <b-col>
                            <b-form-group label="Weeks interval:" label-for="weeks">
                                <b-form-input :id="'weeks'" :type="'number'" :min="0" :step="1" :name="'weeks'" v-model="job.weeks"></b-form-input>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-form-group label="Days interval:" label-for="days">
                                <b-form-input :id="'days'" :type="'number'" :min="0" :step="1" :name="'days'" v-model="job.days"></b-form-input>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-form-group label="Hours interval:" label-for="hours">
                                <b-form-input :id="'hours'" :type="'number'" :min="0" :step="1" :name="'hours'" v-model="job.hours"></b-form-input>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-form-group label="Minutes interval:" label-for="minutes">
                                <b-form-input :id="'minutes'" :type="'number'" :min="0" :step="1" :name="'minutes'" v-model="job.minutes"></b-form-input>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-form-group label="Seconds interval:" label-for="seconds">
                                <b-form-input :id="'seconds'" :type="'number'" :min="0" :step="1" :name="'seconds'" v-model="job.seconds"></b-form-input>
                            </b-form-group>
                        </b-col>
                    </b-row>
                </b-form-group>
                <b-form-group id="" v-if="job.trigger == 'cron'" label="Select cron constraints:" label-for="job-cron">
                    <b-row id="job-cron">
                        <b-col>
                            <b-form-group label="Year:" label-for="year">
                                <b-form-input :id="'year'" :type="'text'" :name="'year'" v-model="job.year"></b-form-input>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-form-group label="Month:" label-for="month">
                                <b-form-input :id="'month'" :type="'text'" :name="'month'" v-model="job.month"></b-form-input>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-form-group label="Day:" label-for="day">
                                <b-form-input :id="'day'" :type="'text'" :name="'day'" v-model="job.day"></b-form-input>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-form-group label="Week:" label-for="dayOfWeek">
                                <b-form-input :id="'dayOfWeek'" :type="'text'" :name="'day_of_week'" v-model="job.day_of_week"></b-form-input>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-form-group label="Hour:" label-for="hour">
                                <b-form-input :id="'hour'" :type="'text'" :name="'hour'" v-model="job.hour"></b-form-input>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-form-group label="Minute:" label-for="minute">
                                <b-form-input :id="'minute'" :type="'text'" :name="'minute'" v-model="job.minute"></b-form-input>
                            </b-form-group>
                        </b-col>
                        <b-col>
                            <b-form-group label="Second:" label-for="second">
                                <b-form-input :id="'second'" :type="'text'" :name="'second'" v-model="job.second"></b-form-input>
                            </b-form-group>
                        </b-col>
                    </b-row>
                </b-form-group>
                <b-form-group
                    id=""
                    v-if="['cron', 'interval'].includes(job.trigger)"
                    label="Optionally select earliest/latest possible date for job to trigger on (inclusive):"
                    label-for="job-runDate">
                    <b-row>
                        <b-col>
                            <vue-ctk-date-time-picker
                                id="job-start-date"
                                :required="'required'"
                                :name="'start_date'"
                                v-model="job.start_date"
                                :format="'YYYY-MM-DD HH:mm:ss'"
                                :formatted="'YYYY-MM-DD HH:mm:ss'"
                                :no-label="true"
                                :label="'Select start date'"/>
                        </b-col>
                        <b-col>
                            <vue-ctk-date-time-picker
                                id="job-end-date"
                                :required="'required'"
                                :name="'end_date'"
                                v-model="job.end_date"
                                :format="'YYYY-MM-DD HH:mm:ss'"
                                :formatted="'YYYY-MM-DD HH:mm:ss'"
                                :output-format="'YYYY-MM-DD HH:mm:ss'"
                                :no-label="true"
                                :label="'Select end date'"/>
                        </b-col>
                    </b-row>
                    
                </b-form-group>
                <div class="text-center mb-3">
                    <b-button @click="submit" type="button" variant="primary">Save</b-button>
                    <b-button variant="danger" :href="cancelTo">Cancel</b-button>
                </div>
            </b-form>
        </div>`,
    methods: {
        submit() {
            this.isSubmitDisabled = true;
            try {
                var job = JSON.parse(JSON.stringify(this.job));
                job.kwargs = JSON.parse(this.job.kwargs);
            } catch (e) {
                this.showMessage("Invalid job data", "danger", "Error");
                this.isSubmitDisabled = false;
                return
            }
            if(this.isUpdate){
                axios.put(
                    `${this.$apiRoutes.jobView}${this.job.id}`,
                    job
                ).then(
                    response => {
                        setTimeout(() => {window.location = this.$frontRoutes.jobsView}, 1000);
                    }
                ).catch(
                    e => {
                        this.isSubmitDisabled = false;
                        console.log(e)
                    }
                )
            } else {
                axios.post(
                    this.$apiRoutes.jobsView,
                    job
                ).then(
                    response => {
                        setTimeout(() => {window.location = this.$frontRoutes.jobsView}, 1000);
                    }
                ).catch(
                    e => {
                        this.isSubmitDisabled = false;
                        console.log(e)
                    }
                )
            }
        },
        getModuleDescription() {
            if (this.availableJobs.find(aj => aj.name == this.job.module)) {
                return this.availableJobs.find(aj => aj.name == this.job.module).job_doc
            } else {
                return ''
            }
        },
        getTriggerDescription() {
            if (this.jobTriggers.find(t => t.name == this.job.trigger)) {
                return this.jobTriggers.find(t => t.name == this.job.trigger).description
            } else {
                return ''
            }
        },
    }
});

    
Vue.component('filter-component', {
    components: {
        Multiselect: window.VueMultiselect.default
    },
    props: {filters: Object},
    template:
        `<b-row>
            <b-col cols="3" class="mb-2 mt-2" v-for="(filter_settings, filter_key) in filters" :key="filter_key">
                <div v-if="filter_settings.type == 'daterange'">
                    <vue-ctk-date-time-picker style="min-height: 42px; font-family: sans-serif; font-size: medium;"
                        :id="filter_key"
                        :name="filter_key"
                        :range="true"
                        @input="$emit('get-items-with-filters', filters)"
                        v-model="filter_settings.value"
                        :format="'YYYY-MM-DD HH:mm:ss'"
                        :formatted="'YYYY-MM-DD HH:mm:ss'"
                        :no-label="false"
                        :label="filter_settings.label"
                    />
                </div>
                <div v-if="filter_settings.type == 'select'">
                    <multiselect
                        :id="filter_key"
                        :ref="filter_key"
                        :name="filter_key"
                        @input="$emit('get-items-with-filters', filters)"
                        v-model="filter_settings.value"
                        :multiple="true"
                        :options="filter_settings.options"
                        :value="filter_settings.value"
                        :select-label="''"
                        :deselect-label="''"
                        :selected-label="''"
                        :preselect-first="false"
                        :block-keys="['Delete']"
                        :placeholder="filter_settings.label"
                        label="label"
                        track-by="id"
                    >
                        <span slot="noResult">Result(s) not found</span>
                    </multiselect>
                </div>
                <div v-if="filter_settings.type == 'text'">
                    <b-form-input
                        class="filter-input"
                        :id="filter_key"
                        @input="$emit('get-items-with-filters', filters)"
                        v-model="filter_settings.value"
                        type="text"
                        :placeholder="filter_settings.label"
                        :name="filter_key">
                    </b-form-input>
                </div>
            </b-col>
        </b-row>`,
});
{% endraw %}