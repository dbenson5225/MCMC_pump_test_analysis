cost_per_cf=importdata('226_pumping_costs.dat');
norm_pump_rate=43700.   % pump rate in ft^3/day
hrs_per_year=4000
cf_per_year=cost_per_cf(:,1)*hrs_per_year*norm_pump_rate/24  % cubic feet per year

% For nonlinear errorbars:
tot=cost_per_cf(:,3); lo1=tot-cost_per_cf(:,2); hi1=cost_per_cf(:,4)-tot;
Theis=cost_per_cf(:,6); lo2=Theis-cost_per_cf(:,5); hi2=cost_per_cf(:,7)-Theis;
nl=cost_per_cf(:,9); lo3=nl-cost_per_cf(:,8); hi3=cost_per_cf(:,10)-nl;


figure(2)
errorbar(cf_per_year,tot,lo1,hi1,'-o')
hold on
errorbar(cf_per_year,Theis,lo2,hi2,'-o')
errorbar(cf_per_year,nl,lo3,hi3,'k-o')
legend('total cost','Theis portion','nonlinear portion','Location','NW')
xlabel('Production rate (cubic feet per year)')
ylabel('Electricity cost per cubic foot ($)')
hold off

figure(3)
errorbar(cf_per_year,tot,lo1,hi1,'-o')
yscale log
hold on
errorbar(cf_per_year,Theis,lo2,hi2,'-o')
errorbar(cf_per_year,nl,lo3,hi3,'k-o')
legend('total cost','Theis portion','nonlinear portion','Location','SE')
xlabel('Production rate (cubic feet per year)')
ylabel('Cost per cubic foot ($)')
hold off
